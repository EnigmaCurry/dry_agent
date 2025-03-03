use anyhow::{Context, Result};
use reqwest::Client;
use serde_json::json;
use uuid::Uuid;

use crate::models::{BotMessage, LlmRequest};

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

        // This is where you'll insert your prompt from earlier
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

        let request = LlmRequest {
            prompt,
            conversation_id: conversation_id.clone(),
        };

        let response = self
            .client
            .post(&self.api_url)
            .json(&json!({
                "prompt": request.prompt,
                "options": {
                    "temperature": 0.7,
                    "max_tokens": 1000
                }
            }))
            .send()
            .await?;

        let json_response: serde_json::Value = response
            .json()
            .await
            .context("Failed to parse LLM response")?;

        // Usually the LLM response would be in a field like "choices[0].message.content"
        // Adjust this according to your LLM API's response structure
        let content = json_response["choices"][0]["message"]["content"]
            .as_str()
            .context("No text content in response")?;

        // Try to parse the JSON response from the LLM
        let bot_message: BotMessage =
            serde_json::from_str(content).context("Failed to parse LLM response as BotMessage")?;

        Ok(bot_message)
    }
}
