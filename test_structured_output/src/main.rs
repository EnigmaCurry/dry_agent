use async_openai::{
    config::OpenAIConfig,
    types::{
        ChatCompletionRequestMessage, ChatCompletionRequestSystemMessage,
        ChatCompletionRequestSystemMessageContent, ChatCompletionRequestUserMessage,
        ChatCompletionRequestUserMessageContent, CreateChatCompletionRequest,
    },
    Client,
};
use serde::{Deserialize, Serialize};
use serde_json::json;

#[derive(Debug, Serialize, Deserialize)]
struct Character {
    name: String,
    occupation: String,
    personality: String,
    background: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct Characters {
    characters: Vec<Character>,
}

#[tokio::main(flavor = "current_thread")]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Initialize OpenAI client with custom URL
    let config = OpenAIConfig::new()
        .with_api_base("http://192.168.1.196:1234/v1")
        .with_api_key("lm-studio");
    let client = Client::with_config(config);

    // Define messages
    let messages = vec![
        ChatCompletionRequestMessage::System(ChatCompletionRequestSystemMessage {
            content: ChatCompletionRequestSystemMessageContent::Text(
                "You are a helpful AI assistant.".to_string(),
            ),
            name: None,
        }),
        ChatCompletionRequestMessage::User(ChatCompletionRequestUserMessage {
            content: ChatCompletionRequestUserMessageContent::Text(
                "Create 1-3 fictional Star Trek characters".to_string(),
            ),
            name: None,
        }),
    ];

    // Define the schema
    let schema = json!({
        "type": "object",
        "properties": {
            "characters": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "occupation": {"type": "string"},
                        "personality": {"type": "string"},
                        "background": {"type": "string"}
                    },
                    "required": ["name", "occupation", "personality", "background"]
                },
                "minItems": 1
            }
        },
        "required": ["characters"]
    });

    // Create chat completion request without response_format initially
    let mut request = CreateChatCompletionRequest {
        model: "your-model".to_string(),
        messages,
        ..Default::default()
    };

    // Use a serde_json::to_value trick to set the field
    let request_value = serde_json::to_value(&request)?;
    let mut request_map = match request_value {
        serde_json::Value::Object(map) => map,
        _ => panic!("Expected request to serialize to an object"),
    };

    // Add the response_format field manually with the correct type
    request_map.insert(
        "response_format".to_string(),
        json!({
            "type": "json_schema",
            "json_schema": {
                "name": "characters",
                "schema": schema
            }
        }),
    );

    // Convert back to request
    let request: CreateChatCompletionRequest =
        serde_json::from_value(serde_json::Value::Object(request_map))?;

    // Send request and get response
    let response = client.chat().create(request).await?;

    // Parse response content
    if let Some(choice) = response.choices.first() {
        if let Some(content) = &choice.message.content {
            let characters: Characters = serde_json::from_str(content)?;
            println!("{}", serde_json::to_string_pretty(&characters)?);
        }
    }

    Ok(())
}
