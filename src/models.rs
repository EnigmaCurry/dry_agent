use serde::{Deserialize, Serialize};
use std::collections::HashMap;

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "snake_case")]
pub enum MessageType {
    Chat,
    Action,
    Confirmation,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(rename_all = "snake_case")]
pub enum ActionType {
    Status,
    Start,
    Stop,
    Restart,
    StartWithTimeout,
    Configure,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ChatContent {
    pub text: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ActionContent {
    pub action_type: ActionType,
    pub services: Vec<String>,
    pub parameters: HashMap<String, serde_json::Value>,
    pub confirmation_required: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ConfirmationContent {
    pub action_id: String,
    pub description: String,
    pub action_details: ActionContent,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct MessageContent {
    #[serde(flatten)]
    pub content: MessageContentEnum,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
#[serde(untagged)]
pub enum MessageContentEnum {
    Chat(ChatContent),
    Action(ActionContent),
    Confirmation(ConfirmationContent),
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct BotMessage {
    pub message_type: MessageType,
    #[serde(flatten)]
    pub content: MessageContent,
    pub conversation_id: String,
}

// For LLM request
#[derive(Debug, Serialize, Deserialize)]
pub struct LlmRequest {
    pub prompt: String,
    pub conversation_id: String,
}

// For MQTT
#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct MqttActionMessage {
    pub action_type: ActionType,
    pub services: Vec<String>,
    pub parameters: HashMap<String, serde_json::Value>,
    pub request_id: String,
}
