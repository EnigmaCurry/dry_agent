use anyhow::{Context, Result};
use matrix_sdk::{
    config::SyncSettings,
    ruma::{events::room::message::RoomMessageEventContent, OwnedRoomId, OwnedUserId},
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
        // Make sure we're parsing the URL correctly
        let homeserver_url =
            url::Url::parse(&config.matrix_homeserver).context("Invalid homeserver URL")?;

        let client = Client::builder()
            .homeserver_url(homeserver_url)
            .build()
            .await?;

        let llm_client = LlmClient::new(config.llm_api_url.clone());

        let mqtt_client = MqttClient::new(
            config.mqtt_broker.clone(),
            config.mqtt_port,
            "dry_agent_bot",
            config.mqtt_topic.clone(),
        )?;

        Ok(Self {
            client,
            llm_client,
            mqtt_client: Arc::new(Mutex::new(mqtt_client)),
            pending_confirmations: Arc::new(Mutex::new(HashMap::new())),
            config,
        })
    }

    pub async fn login(&self) -> Result<()> {
        self.client
            .matrix_auth()
            .login_username(&self.config.matrix_username, &self.config.matrix_password)
            .initial_device_display_name("dry_agent")
            .send()
            .await?;

        println!("Logged in as {}", self.config.matrix_username);
        Ok(())
    }

    pub async fn start(&self) -> Result<()> {
        let user_id = self.client.user_id().context("Not logged in")?.to_owned();

        let bot = self.clone();

        // Use add_event_handler with the correct content access
        self.client.add_event_handler(
            move |event: matrix_sdk::ruma::events::room::message::OriginalSyncRoomMessageEvent,
                  room: matrix_sdk::Room| {
                let bot = bot.clone();
                let user_id = user_id.clone();

                async move {
                    // Don't respond to our own messages
                    if event.sender != user_id {
                        // Extract the message text based on the message type
                        if let Some(text) = get_message_text(&event.content) {
                            let owned_sender = event.sender.clone();
                            bot.handle_message(room, &owned_sender, &text).await;
                        }
                    }
                }
            },
        );

        self.client.sync(SyncSettings::default()).await?;
        Ok(())
    }

    async fn handle_message(&self, room: matrix_sdk::Room, sender: &OwnedUserId, message: &str) {
        println!("Received message from {}: {}", sender, message);

        // Check if this is a confirmation response
        if let Some(confirmation_id) = self.extract_confirmation_id(message) {
            if message.to_lowercase().contains("yes") || message.to_lowercase().contains("confirm")
            {
                // Convert room_id() to OwnedRoomId
                let room_id = room.room_id().to_owned();
                self.handle_confirmation(&room_id, confirmation_id, true)
                    .await;
                return;
            } else if message.to_lowercase().contains("no")
                || message.to_lowercase().contains("cancel")
            {
                // Convert room_id() to OwnedRoomId
                let room_id = room.room_id().to_owned();
                self.handle_confirmation(&room_id, confirmation_id, false)
                    .await;
                return;
            }
        }

        // Process with LLM
        match self.llm_client.process_message(message).await {
            Ok(bot_message) => {
                // Convert room_id() to OwnedRoomId
                let room_id = room.room_id().to_owned();
                self.handle_bot_message(&room_id, bot_message).await;
            }
            Err(e) => {
                eprintln!("Error processing message: {:?}", e);
                // Use the updated API for sending messages
                let content = RoomMessageEventContent::text_plain(
                    "Sorry, I encountered an error processing your request.",
                );
                let _ = room.send(content).await;
            }
        }
    }

    async fn handle_bot_message(&self, room_id: &OwnedRoomId, bot_message: BotMessage) {
        match bot_message.message_type {
            MessageType::Chat => {
                if let Ok(content) = serde_json::from_value::<crate::models::ChatContent>(
                    serde_json::to_value(bot_message.content.content).unwrap(),
                ) {
                    if let Some(room) = self.client.get_room(room_id) {
                        let message = RoomMessageEventContent::text_plain(&content.text);
                        let _ = room.send(message).await;
                    }
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
                            "Sorry, I encountered an error executing your request.",
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
                    "Sorry, I encountered an error executing your request.",
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
            llm_client: LlmClient::new(self.config.llm_api_url.clone()),
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
