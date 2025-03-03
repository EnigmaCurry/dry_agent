use anyhow::{Context, Result};
use reqwest::Client;
use serde_json::json;
use uuid::Uuid;

use crate::models::BotMessage;

pub struct LlmClient {
    client: Client,
    api_url: String,
}

impl LlmClient {
    pub fn new(api_url: String) -> Self {
        Self {
            client: Client::new(),
            api_url,
        }
    }

    pub async fn process_message(&self, user_message: &str) -> Result<BotMessage> {
        let conversation_id = Uuid::new_v4().to_string();
        println!("Sending request to LLM API: {}", self.api_url);

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
                            "if": {
                                "properties": {
                                    "message_type": { "enum": ["chat"] }
                                }
                            }
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
                            "if": {
                                "properties": {
                                    "message_type": { "enum": ["action"] }
                                }
                            }
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
                            "if": {
                                "properties": {
                                    "message_type": { "enum": ["confirmation"] }
                                }
                            }
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

        let prompt = format!(
            r#"You are dry_agent, a ChatOps bot that helps users manage Docker services via Matrix chat. Your responses must be formatted as structured JSON that clearly identifies whether you're providing:

1. A general chat response (message_type: "chat")
2. A container action request (message_type: "action") 
3. A confirmation request (message_type: "confirmation")

## Message Structure Rules:

- Always assess if the user is requesting a Docker-related action or just chatting
- Use "chat" type for general conversation, questions, or when clarification is needed
- Use "action" type only when the user clearly requests a specific Docker operation
- Use "confirmation" type when additional verification is needed before executing actions
- Always include "conversation_id" in your responses (use "{}" for now)

## Valid Actions:
- status: Check running containers
- start: Launch containers
- stop: Halt containers
- restart: Restart containers
- start_with_timeout: Start containers and stop after specified minutes
- configure: Set up new services (requires additional information)

## JSON Response Format:

For chat responses:
```json
{{
  "message_type": "chat",
  "content": {{
    "text": "Your friendly message here"
  }},
  "conversation_id": "{}"
}}
```

For action responses:
```json
{{
  "message_type": "action",
  "content": {{
    "action_type": "status|start|stop|restart|start_with_timeout|configure",
    "services": ["service1", "service2"],
    "parameters": {{
      // Action-specific parameters
    }},
    "confirmation_required": true|false
  }},
  "conversation_id": "{}"
}}
```

For confirmation responses:
```json
{{
  "message_type": "confirmation",
  "content": {{
    "action_id": "action123",
    "description": "Summary of action requiring confirmation",
    "action_details": {{
      // Copy of action content
    }}
  }},
  "conversation_id": "{}"
}}
```

User: "{}"
"#,
            conversation_id, conversation_id, conversation_id, conversation_id, user_message
        );

        let response = self
            .client
            .post(&self.api_url)
            .json(&json!({
                "prompt": prompt,
                "temperature": 0.7,
                "max_tokens": 1000
            }))
            .send()
            .await?;

        // Get the response
        let response_text = response.text().await?;
        println!("Raw LLM response: {}", response_text);

        // Parse the response
        let json_response: serde_json::Value =
            serde_json::from_str(&response_text).context("Failed to parse LLM response as JSON")?;

        // Extract the content from the response
        let content = json_response["choices"][0]["text"]
            .as_str()
            .context("No text content in response")?;

        println!("Extracted content from LLM: {}", content);

        // Extract just the JSON part from the content
        let json_content = extract_json_from_text(content);
        println!("Extracted JSON content: {}", json_content);

        // Parse to an intermediate structure that matches the JSON
        #[derive(serde::Deserialize)]
        struct LlmResponse {
            message_type: String,
            content: serde_json::Value,
            conversation_id: String,
        }

        // First parse to the intermediate format
        match serde_json::from_str::<LlmResponse>(&json_content) {
            Ok(llm_resp) => {
                println!("Successfully parsed LLM JSON response");

                // Then convert to your actual BotMessage format
                let message_type = match llm_resp.message_type.as_str() {
                    "chat" => crate::models::MessageType::Chat,
                    "action" => crate::models::MessageType::Action,
                    "confirmation" => crate::models::MessageType::Confirmation,
                    _ => {
                        return Err(anyhow::anyhow!(
                            "Unknown message type: {}",
                            llm_resp.message_type
                        ))
                    }
                };

                // Create the appropriate MessageContentEnum variant
                let content_enum = match llm_resp.message_type.as_str() {
                    "chat" => {
                        // Parse the chat content
                        if let Ok(chat_content) =
                            serde_json::from_value::<crate::models::ChatContent>(llm_resp.content)
                        {
                            crate::models::MessageContentEnum::Chat(chat_content)
                        } else {
                            return Err(anyhow::anyhow!("Invalid chat content structure"));
                        }
                    }
                    "action" => {
                        // Parse the action content
                        if let Ok(action_content) =
                            serde_json::from_value::<crate::models::ActionContent>(llm_resp.content)
                        {
                            crate::models::MessageContentEnum::Action(action_content)
                        } else {
                            return Err(anyhow::anyhow!("Invalid action content structure"));
                        }
                    }
                    "confirmation" => {
                        // Parse the confirmation content
                        if let Ok(confirmation_content) = serde_json::from_value::<
                            crate::models::ConfirmationContent,
                        >(llm_resp.content)
                        {
                            crate::models::MessageContentEnum::Confirmation(confirmation_content)
                        } else {
                            return Err(anyhow::anyhow!("Invalid confirmation content structure"));
                        }
                    }
                    _ => {
                        return Err(anyhow::anyhow!(
                            "Unknown message type: {}",
                            llm_resp.message_type
                        ))
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

                Ok(bot_message)
            }
            Err(e) => {
                eprintln!("Failed to parse LLM response: {}", e);

                // Create fallback message
                let fallback_message = BotMessage {
                message_type: crate::models::MessageType::Chat,
                content: crate::models::MessageContent {
                    content: crate::models::MessageContentEnum::Chat(
                        crate::models::ChatContent {
                            text: format!("I received your message but had trouble processing it correctly. Technical error: {}", e)
                        }
                    ),
                },
                conversation_id: Uuid::new_v4().to_string(),
            };

                Ok(fallback_message)
            }
        }
    }
}

fn extract_json_from_text(text: &str) -> String {
    // Try to find JSON between ```json and ``` markers
    if let (Some(start), Some(end)) = (text.find("```json"), text.rfind("```")) {
        let start_pos = start + "```json".len();
        let json_content = &text[start_pos..end].trim();
        return json_content.to_string();
    }

    // Try to find JSON between ``` and ``` markers (without "json" specifier)
    if let (Some(start), Some(end)) = (text.find("```"), text.rfind("```")) {
        let start_pos = start + "```".len();
        let json_content = &text[start_pos..end].trim();
        return json_content.to_string();
    }

    // Try to find a complete JSON object
    if let (Some(start), Some(end)) = (text.find("{"), text.rfind("}")) {
        let json_content = &text[start..=end];
        return json_content.to_string();
    }

    // Fallback to the whole text
    text.to_string()
}
