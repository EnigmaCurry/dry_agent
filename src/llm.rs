use anyhow::Result;
use async_openai::{
    config::OpenAIConfig,
    types::{
        ChatCompletionRequestMessage, ChatCompletionRequestSystemMessage,
        ChatCompletionRequestSystemMessageContent, ChatCompletionRequestUserMessage,
        ChatCompletionRequestUserMessageContent, CreateChatCompletionRequest,
    },
    Client,
};
use serde_json::json;
use std::error::Error;
use uuid::Uuid;

use crate::models::BotMessage;

pub struct LlmClient {
    client: Client<OpenAIConfig>,
    model: String,
}

impl LlmClient {
    pub fn new(base_url: String, model: String) -> Self {
        // Configure OpenAI client with custom URL
        let config = OpenAIConfig::new()
            .with_api_base(&base_url)
            .with_api_key("lm-studio"); // Using a placeholder API key

        Self {
            client: Client::with_config(config),
            model: model,
        }
    }

    pub async fn process_message(&self, user_message: &str) -> Result<BotMessage> {
        let conversation_id = Uuid::new_v4().to_string();
        self.chat_completions_with_schema(user_message, &conversation_id)
            .await
    }

    async fn chat_completions_with_schema(
        &self,
        user_message: &str,
        conversation_id: &str,
    ) -> Result<BotMessage> {
        println!("Using async-openai with JSON schema");

        // Define the JSON Schema for the response
        let bot_message_schema = json!({
            "type": "object",
            "properties": {
                "message_type": {
                    "type": "string",
                    "enum": ["chat", "action", "confirmation"],
                    "description": "The type of message being sent"
                },
                "content": {
                    "type": "object",
                    "oneOf": [
                        {
                            "type": "object",
                            "properties": {
                                "text": {
                                    "type": "string",
                                    "description": "The chat message text"
                                }
                            },
                            "required": ["text"],
                            "additionalProperties": false,
                        },
                        {
                            "type": "object",
                            "properties": {
                                "action_type": {
                                    "type": "string",
                                    "enum": ["status", "start", "stop", "restart", "start_with_timeout", "configure"],
                                    "description": "The type of action to perform"
                                },
                                "services": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    },
                                    "description": "List of service names to act upon"
                                },
                                "parameters": {
                                    "type": "object",
                                    "description": "Action-specific parameters"
                                },
                                "confirmation_required": {
                                    "type": "boolean",
                                    "description": "Whether this action requires confirmation"
                                }
                            },
                            "required": ["action_type", "services", "parameters", "confirmation_required"],
                            "additionalProperties": false,
                        },
                        {
                            "type": "object",
                            "properties": {
                                "action_id": {
                                    "type": "string",
                                    "description": "Unique identifier for the action"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "Description of the action requiring confirmation"
                                },
                                "action_details": {
                                    "type": "object",
                                    "properties": {
                                        "action_type": {
                                            "type": "string",
                                            "enum": ["status", "start", "stop", "restart", "start_with_timeout", "configure"]
                                        },
                                        "services": {
                                            "type": "array",
                                            "items": {
                                                "type": "string"
                                            }
                                        },
                                        "parameters": {
                                            "type": "object"
                                        }
                                    },
                                    "required": ["action_type", "services", "parameters"],
                                    "additionalProperties": false
                                }
                            },
                            "required": ["action_id", "description", "action_details"],
                            "additionalProperties": false,
                        }
                    ]
                },
                "conversation_id": {
                    "type": "string",
                    "description": "Unique identifier for the conversation"
                }
            },
            "required": ["message_type", "content", "conversation_id"],
            "additionalProperties": false
        });

        // Define messages
        let messages = vec![
            ChatCompletionRequestMessage::System(ChatCompletionRequestSystemMessage {
                content: ChatCompletionRequestSystemMessageContent::Text(
                    "You are dry_agent, a ChatOps bot that helps users manage Docker services via Matrix chat.".to_string(),
                ),
                name: None,
            }),
            ChatCompletionRequestMessage::User(ChatCompletionRequestUserMessage {
                content: ChatCompletionRequestUserMessageContent::Text(
                    user_message.to_string(),
                ),
                name: None,
            }),
        ];

        // Create chat completion request
        let request = CreateChatCompletionRequest {
            model: self.model.clone(),
            messages,
            temperature: Some(0.7),
            ..Default::default()
        };

        // Use a serde_json::to_value trick to set the response_format field
        let request_value = serde_json::to_value(&request)?;
        let mut request_map = match request_value {
            serde_json::Value::Object(map) => map,
            _ => {
                return Err(anyhow::anyhow!(
                    "Expected request to serialize to an object"
                ))
            }
        };

        // Add the response_format field manually with the correct type
        request_map.insert(
            "response_format".to_string(),
            json!({
                "type": "json_schema",
                "json_schema": {
                    "name": "bot_message",
                    "schema": bot_message_schema
                }
            }),
        );

        // Convert back to request
        let request_json = serde_json::Value::Object(request_map.clone());
        println!(
            "Sending request: {}",
            serde_json::to_string_pretty(&request_json)?
        );

        let request: CreateChatCompletionRequest =
            serde_json::from_value(serde_json::Value::Object(request_map))?;

        // Send request and capture any error details
        let response = match self.client.chat().create(request).await {
            Ok(response) => {
                println!("API call succeeded!");
                response
            }
            Err(e) => {
                // Print detailed error information
                println!("API call failed with error: {}", e);

                // Print the error type information
                println!("Error type: {}", std::any::type_name_of_val(&e));

                // Simplify this to just print the error without matching on specific variants
                println!("Error details: {:?}", e);

                // Error chain (safe approach)
                let mut current_error: &dyn Error = &e;
                let mut indent = 0;

                println!("Error chain:");
                loop {
                    println!("{:indent$}{}", "", current_error, indent = indent);
                    indent += 2;

                    if let Some(source) = current_error.source() {
                        current_error = source;
                    } else {
                        break;
                    }
                }

                // Return a more descriptive error
                return Err(anyhow::anyhow!("Failed to create chat completion: {}", e));
            }
        };

        // Debug: Print the full response for inspection
        println!("Full response structure: {:#?}", response);

        // Parse response content
        if let Some(choice) = response.choices.first() {
            println!("First choice: {:#?}", choice);

            if let Some(content) = &choice.message.content {
                println!("Raw response content: {}", content);

                // Try to parse the content as JSON first
                match serde_json::from_str::<serde_json::Value>(content) {
                    Ok(json_value) => {
                        println!(
                            "Content is valid JSON: {}",
                            serde_json::to_string_pretty(&json_value)?
                        );
                    }
                    Err(e) => {
                        println!("Content is not valid JSON: {}", e);

                        // Create a fallback chat message
                        let fallback = BotMessage {
                            message_type: crate::models::MessageType::Chat,
                            content: crate::models::MessageContent {
                                content: crate::models::MessageContentEnum::Chat(
                                    crate::models::ChatContent {
                                        text: content.clone(),
                                    },
                                ),
                            },
                            conversation_id: conversation_id.to_string(),
                        };

                        return Ok(fallback);
                    }
                }

                // Parse the content into a BotMessage
                match parse_llm_response(content) {
                    Ok(mut bot_message) => {
                        // Ensure conversation_id is set correctly
                        if bot_message.conversation_id.is_empty() {
                            bot_message.conversation_id = conversation_id.to_string();
                        }

                        return Ok(bot_message);
                    }
                    Err(e) => {
                        println!("Error parsing LLM response: {}", e);

                        // Try to create a default response with the raw content
                        let default_message = BotMessage {
                            message_type: crate::models::MessageType::Chat,
                            content: crate::models::MessageContent {
                                content: crate::models::MessageContentEnum::Chat(
                                    crate::models::ChatContent {
                                        text: content.clone(),
                                    },
                                ),
                            },
                            conversation_id: conversation_id.to_string(),
                        };

                        return Ok(default_message);
                    }
                }
            } else {
                println!("No content field in the response choice");
            }
        } else {
            println!("No choices in the response");
        }

        Err(anyhow::anyhow!(
            "No valid content in chat completion response"
        ))
    }
}

// Helper function to parse LLM response JSON into a BotMessage
fn parse_llm_response(json_content: &str) -> Result<BotMessage> {
    println!("Attempting to parse JSON content: {}", json_content);

    // First check if the content is valid JSON
    if let Err(json_err) = serde_json::from_str::<serde_json::Value>(json_content) {
        println!("Content is not valid JSON: {}", json_err);
        return Err(anyhow::anyhow!("Invalid JSON content: {}", json_err));
    }

    // Parse to an intermediate structure that matches the JSON
    #[derive(serde::Deserialize, Debug)]
    struct LlmResponse {
        message_type: String,
        content: serde_json::Value,
        conversation_id: String,
    }

    // Parse to the intermediate format
    let llm_resp: LlmResponse = match serde_json::from_str(json_content) {
        Ok(resp) => {
            println!("Successfully parsed to LlmResponse: {:?}", resp);
            resp
        }
        Err(e) => {
            println!("Failed to parse to LlmResponse: {}", e);
            return Err(anyhow::anyhow!("Failed to parse LLM JSON response: {}", e));
        }
    };

    // Convert to actual BotMessage format
    let message_type = match llm_resp.message_type.as_str() {
        "chat" => crate::models::MessageType::Chat,
        "action" => crate::models::MessageType::Action,
        "confirmation" => crate::models::MessageType::Confirmation,
        unknown => {
            println!("Unknown message type: {}", unknown);
            return Err(anyhow::anyhow!("Unknown message type: {}", unknown));
        }
    };

    // Create the appropriate MessageContentEnum variant
    let content_enum = match llm_resp.message_type.as_str() {
        "chat" => {
            // Parse the chat content
            match serde_json::from_value::<crate::models::ChatContent>(llm_resp.content.clone()) {
                Ok(chat_content) => {
                    println!("Successfully parsed chat content");
                    crate::models::MessageContentEnum::Chat(chat_content)
                }
                Err(e) => {
                    println!("Failed to parse chat content: {}", e);
                    println!("Raw content value: {}", llm_resp.content);
                    return Err(anyhow::anyhow!("Invalid chat content structure: {}", e));
                }
            }
        }
        "action" => {
            // Parse the action content
            match serde_json::from_value::<crate::models::ActionContent>(llm_resp.content.clone()) {
                Ok(action_content) => {
                    println!("Successfully parsed action content");
                    crate::models::MessageContentEnum::Action(action_content)
                }
                Err(e) => {
                    println!("Failed to parse action content: {}", e);
                    println!("Raw content value: {}", llm_resp.content);
                    return Err(anyhow::anyhow!("Invalid action content structure: {}", e));
                }
            }
        }
        "confirmation" => {
            // Parse the confirmation content
            match serde_json::from_value::<crate::models::ConfirmationContent>(
                llm_resp.content.clone(),
            ) {
                Ok(confirmation_content) => {
                    println!("Successfully parsed confirmation content");
                    crate::models::MessageContentEnum::Confirmation(confirmation_content)
                }
                Err(e) => {
                    println!("Failed to parse confirmation content: {}", e);
                    println!("Raw content value: {}", llm_resp.content);
                    return Err(anyhow::anyhow!(
                        "Invalid confirmation content structure: {}",
                        e
                    ));
                }
            }
        }
        _ => {
            return Err(anyhow::anyhow!(
                "Unknown message type: {}",
                llm_resp.message_type
            ));
        }
    };

    // Create the properly structured BotMessage
    let bot_message = BotMessage {
        message_type,
        content: crate::models::MessageContent {
            content: content_enum,
        },
        conversation_id: llm_resp.conversation_id,
    };

    println!("Successfully created BotMessage");
    Ok(bot_message)
}
