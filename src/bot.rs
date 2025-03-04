use anyhow::{Context, Result};
use matrix_sdk::{
    config::SyncSettings,
    ruma::{
        events::room::member::StrippedRoomMemberEvent,
        events::room::message::RoomMessageEventContent, OwnedRoomId, OwnedUserId,
    },
    Client,
};
use std::collections::HashMap;
use std::sync::Arc;
use tokio::sync::Mutex;
use uuid::Uuid;

use crate::{
    config::Config,
    llm::LlmClient,
    models::{BotMessage, MessageType, MqttActionMessage},
    mqtt::MqttClient,
};

pub struct Bot {
    client: Client,
    llm_client: LlmClient,
    mqtt_client: Arc<Mutex<MqttClient>>,
    pending_confirmations: Arc<Mutex<HashMap<String, MqttActionMessage>>>,
    config: Config,
}

impl Bot {
    pub async fn new(config: Config) -> Result<Self> {
        let homeserver_url =
            reqwest::Url::parse(&config.matrix_homeserver).context("Invalid homeserver URL")?;

        // Ensure the store directory exists
        if !config.matrix_store_path.exists() {
            std::fs::create_dir_all(&config.matrix_store_path)?;
        }

        // Build the client with the store
        let client = Client::builder()
            .homeserver_url(homeserver_url)
            .sqlite_store(config.matrix_store_path.join("matrix-store.db"), None)
            .build()
            .await?;

        // Create the bot instance
        let bot = Self {
            client,
            llm_client: LlmClient::new(config.llm_api_url.clone(), config.llm_model.clone()),
            mqtt_client: Arc::new(Mutex::new(MqttClient::new(
                config.mqtt_broker.clone(),
                config.mqtt_port,
                "dry_agent_bot",
                config.mqtt_topic.clone(),
                config.mqtt_client_cert.clone(),
                config.mqtt_client_key.clone(),
                config.mqtt_ca_cert.clone(),
            )?)),
            pending_confirmations: Arc::new(Mutex::new(HashMap::new())),
            config,
        };

        Ok(bot)
    }

    pub async fn login(&self) -> Result<()> {
        // Simple login without trying to control the device ID
        self.client
            .matrix_auth()
            .login_username(&self.config.matrix_username, &self.config.matrix_password)
            .initial_device_display_name("dry_agent")
            .send()
            .await?;

        println!("Logged into matrix as {}", self.config.matrix_username);

        // Display the device ID for verification purposes
        if let Some(device_id) = self.client.device_id() {
            println!(
                "Device ID: {} - You can verify this device in Element",
                device_id
            );
        }

        Ok(())
    }

    pub async fn display_verification_status(&self) -> Result<()> {
        if let Some(user_id) = self.client.user_id() {
            println!("=== Device Verification Status ===");
            println!("Logged in as: {}", user_id);

            if let Some(device_id) = self.client.device_id() {
                println!("Current device ID: {}", device_id);

                // Since we can't easily check verification status through the API,
                // we'll just display information to help with manual verification
                println!("To verify this device:");
                println!("1. Log into the bot account in Element");
                println!("2. Go to Settings > Security & Privacy > Sessions");
                println!("3. Find the device with ID: {}", device_id);
                println!("4. Click 'Verify' to verify this device");
            } else {
                println!("No device ID available");
            }

            println!("================================");
        } else {
            println!("Not logged in");
        }

        Ok(())
    }

    pub async fn start(&self) -> Result<()> {
        let user_id = self.client.user_id().context("Not logged in")?.to_owned();

        // Set up message handler with deduplication
        let bot = self.clone();
        self.client.add_event_handler(
            move |event: matrix_sdk::ruma::events::room::message::OriginalSyncRoomMessageEvent,
                  room: matrix_sdk::Room| {
                let bot = bot.clone();
                let user_id = user_id.clone();

                async move {
                    // Don't respond to our own messages
                    if event.sender == user_id {
                        return;
                    }

                    // Extract the message text and process as before
                    if let Some(text) = get_message_text(&event.content) {
                        let owned_sender = event.sender.clone();

                        // Only process the message now that we know it's new
                        if let Err(e) = bot.handle_message(room, &owned_sender, &text).await {
                            eprintln!("Error handling message: {:?}", e);
                        }
                    }
                }
            },
        );

        // Add room invite handler
        self.client.add_event_handler(
            |event: StrippedRoomMemberEvent, client: matrix_sdk::Client, room: matrix_sdk::Room| {
                async move {
                    // Get our own user_id
                    let our_user_id = client.user_id().expect("Client should be logged in");

                    // Check if this event is an invite for our user
                    if event.state_key != our_user_id {
                        return; // Not for us
                    }

                    if event.content.membership
                        == matrix_sdk::ruma::events::room::member::MembershipState::Invite
                    {
                        // Use the room's room_id
                        let room_id = room.room_id();
                        println!("Received invite to room {} from {}", room_id, event.sender);

                        match client.join_room_by_id(room_id).await {
                            Ok(_) => println!("Successfully joined room {}", room_id),
                            Err(e) => eprintln!("Failed to join room {}: {:?}", room_id, e),
                        }
                    }
                }
            },
        );

        println!("Starting sync, bot is now running...");

        // Modify to actually sync continuously
        let settings = SyncSettings::default();
        self.client.sync(settings).await?;

        Ok(())
    }

    async fn handle_message(
        &self,
        room: matrix_sdk::Room,
        sender: &OwnedUserId,
        message: &str,
    ) -> Result<()> {
        println!("========== START HANDLING MESSAGE ==========");
        println!("Message from {}: {}", sender, message);

        // Check if this is a confirmation response
        if let Some(confirmation_id) = self.extract_confirmation_id(message) {
            println!("Detected confirmation ID: {}", confirmation_id);
            if message.to_lowercase().contains("yes") || message.to_lowercase().contains("confirm")
            {
                println!("Processing as CONFIRM");
                let room_id = room.room_id().to_owned();
                self.handle_confirmation(&room_id, confirmation_id, true)
                    .await;
                println!("========== END HANDLING MESSAGE (CONFIRMATION) ==========");
                return Ok(());
            } else if message.to_lowercase().contains("no")
                || message.to_lowercase().contains("cancel")
            {
                println!("Processing as CANCEL");
                let room_id = room.room_id().to_owned();
                self.handle_confirmation(&room_id, confirmation_id, false)
                    .await;
                println!("========== END HANDLING MESSAGE (CANCELLATION) ==========");
                return Ok(());
            }
        }

        // Process with LLM
        println!("Processing with LLM");
        match self.llm_client.process_message(message).await {
            Ok(bot_message) => {
                println!("LLM processing successful!");
                let room_id = room.room_id().to_owned();
                self.handle_bot_message(&room_id, bot_message).await;
                println!("========== END HANDLING MESSAGE (SUCCESS) ==========");
                Ok(())
            }
            Err(e) => {
                println!("LLM processing failed with error: {:?}", e);
                eprintln!("Error processing message: {:?}", e);
                let content = RoomMessageEventContent::text_plain(&format!(
                    "Sorry, I encountered an error processing your dumb request: {}",
                    e
                ));
                println!("Sending error message to room");
                room.send(content).await?;
                println!("========== END HANDLING MESSAGE (ERROR) ==========");
                Err(anyhow::anyhow!("Failed to process message: {}", e))
            }
        }
    }

    async fn handle_bot_message(&self, room_id: &OwnedRoomId, bot_message: BotMessage) {
        println!("====== START HANDLE_BOT_MESSAGE ======");
        println!("Message type: {:?}", bot_message.message_type);

        match bot_message.message_type {
            MessageType::Chat => {
                println!("Processing CHAT message");
                if let Ok(content) = serde_json::from_value::<crate::models::ChatContent>(
                    serde_json::to_value(bot_message.content.content).unwrap(),
                ) {
                    println!("Successfully parsed chat content: {}", content.text);
                    if let Some(room) = self.client.get_room(room_id) {
                        let message = RoomMessageEventContent::text_plain(&content.text);
                        println!("Sending chat message to room");
                        let _ = room.send(message).await;
                    } else {
                        println!("Failed to get room with ID {}", room_id);
                    }
                } else {
                    println!("Failed to parse chat content from value");
                }
            }
            MessageType::Action => {
                if let Ok(content) = serde_json::from_value::<crate::models::ActionContent>(
                    serde_json::to_value(bot_message.content.content).unwrap(),
                ) {
                    if content.confirmation_required {
                        // Create a confirmation request
                        let action_id = Uuid::new_v4().to_string();
                        let confirmation_message = format!(
                            "I'll perform this action: {:?} on services: {:?}. Reply with 'confirm {}' to proceed or 'cancel {}' to abort.",
                            content.action_type,
                            content.services,
                            action_id,
                            action_id
                        );

                        // Store the action for later confirmation
                        let mqtt_action = MqttActionMessage {
                            action_type: content.action_type,
                            services: content.services,
                            parameters: content.parameters,
                            request_id: action_id.clone(),
                        };

                        self.pending_confirmations
                            .lock()
                            .await
                            .insert(action_id, mqtt_action);

                        if let Some(room) = self.client.get_room(room_id) {
                            let message =
                                RoomMessageEventContent::text_plain(&confirmation_message);
                            let _ = room.send(message).await;
                        }
                    } else {
                        // Execute immediately
                        self.execute_action(room_id, content).await;
                    }
                }
            }
            MessageType::Confirmation => {
                if let Ok(content) = serde_json::from_value::<crate::models::ConfirmationContent>(
                    serde_json::to_value(bot_message.content.content).unwrap(),
                ) {
                    let action_id = content.action_id;
                    let confirmation_message = format!(
                        "{} Reply with 'confirm {}' to proceed or 'cancel {}' to abort.",
                        content.description, action_id, action_id
                    );

                    // Store the action for later confirmation
                    let mqtt_action = MqttActionMessage {
                        action_type: content.action_details.action_type,
                        services: content.action_details.services,
                        parameters: content.action_details.parameters,
                        request_id: action_id.clone(),
                    };

                    self.pending_confirmations
                        .lock()
                        .await
                        .insert(action_id, mqtt_action);

                    if let Some(room) = self.client.get_room(room_id) {
                        let message = RoomMessageEventContent::text_plain(&confirmation_message);
                        let _ = room.send(message).await;
                    }
                }
            }
        }
        println!("====== END HANDLE_BOT_MESSAGE ======");
    }

    async fn handle_confirmation(
        &self,
        room_id: &OwnedRoomId,
        confirmation_id: String,
        confirmed: bool,
    ) {
        let mut pending = self.pending_confirmations.lock().await;

        if let Some(action) = pending.remove(&confirmation_id) {
            if confirmed {
                // Execute the action
                let mut mqtt_client = self.mqtt_client.lock().await;
                if let Err(e) = mqtt_client.send_action(action.clone()) {
                    eprintln!("Error sending action to MQTT: {:?}", e);
                    if let Some(room) = self.client.get_room(room_id) {
                        let message = RoomMessageEventContent::text_plain(
                            "Sorry, I encountered an error executing your confirmation.",
                        );
                        let _ = room.send(message).await;
                    }
                    return;
                }

                if let Some(room) = self.client.get_room(room_id) {
                    let message = RoomMessageEventContent::text_plain(&format!(
                        "Action confirmed! Executing {:?} on services: {:?}.",
                        action.action_type, action.services
                    ));
                    let _ = room.send(message).await;
                }
            } else {
                if let Some(room) = self.client.get_room(room_id) {
                    let message = RoomMessageEventContent::text_plain("Action cancelled.");
                    let _ = room.send(message).await;
                }
            }
        } else {
            if let Some(room) = self.client.get_room(room_id) {
                let message = RoomMessageEventContent::text_plain(
                    "I couldn't find that confirmation request. It may have expired.",
                );
                let _ = room.send(message).await;
            }
        }
    }

    async fn execute_action(&self, room_id: &OwnedRoomId, content: crate::models::ActionContent) {
        let mqtt_action = MqttActionMessage {
            action_type: content.action_type,
            services: content.services,
            parameters: content.parameters,
            request_id: Uuid::new_v4().to_string(),
        };

        let mut mqtt_client = self.mqtt_client.lock().await;
        if let Err(e) = mqtt_client.send_action(mqtt_action.clone()) {
            eprintln!("Error sending action to MQTT: {:?}", e);
            if let Some(room) = self.client.get_room(room_id) {
                let message = RoomMessageEventContent::text_plain(
                    "Sorry, I encountered an error executing your action request.",
                );
                let _ = room.send(message).await;
            }
            return;
        }

        if let Some(room) = self.client.get_room(room_id) {
            let message = RoomMessageEventContent::text_plain(&format!(
                "Executing {:?} on services: {:?}.",
                mqtt_action.action_type, mqtt_action.services
            ));
            let _ = room.send(message).await;
        }
    }

    fn extract_confirmation_id(&self, message: &str) -> Option<String> {
        // Simple regex-free parser for "confirm <id>" or "cancel <id>"
        let lower_message = message.to_lowercase();

        if lower_message.contains("confirm") || lower_message.contains("cancel") {
            let parts: Vec<&str> = message.split_whitespace().collect();
            if parts.len() >= 2 {
                // The last word might be the ID
                return Some(parts.last().unwrap().to_string());
            }
        }

        None
    }
}

impl Clone for Bot {
    fn clone(&self) -> Self {
        Self {
            client: self.client.clone(),
            llm_client: LlmClient::new(
                self.config.llm_api_url.clone(),
                self.config.llm_model.clone(),
            ),
            mqtt_client: self.mqtt_client.clone(),
            pending_confirmations: self.pending_confirmations.clone(),
            config: self.config.clone(),
        }
    }
}

// Helper function to extract text from different message types
// Now returns an owned String instead of a reference
fn get_message_text(content: &RoomMessageEventContent) -> Option<String> {
    match &content.msgtype {
        matrix_sdk::ruma::events::room::message::MessageType::Text(text_msg) => {
            Some(text_msg.body.clone())
        }
        matrix_sdk::ruma::events::room::message::MessageType::Notice(notice_msg) => {
            Some(notice_msg.body.clone())
        }
        // Handle other message types if needed
        _ => None,
    }
}
