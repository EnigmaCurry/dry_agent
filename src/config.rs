use anyhow::Result;
use serde::Deserialize;
use std::env;

#[derive(Debug, Deserialize, Clone)]
pub struct Config {
    pub matrix_homeserver: String,
    pub matrix_username: String,
    pub matrix_password: String,
    pub llm_api_url: String,
    pub mqtt_broker: String,
    pub mqtt_port: u16,
    pub mqtt_topic: String,
}

impl Config {
    pub fn from_env() -> Result<Self> {
        dotenv::dotenv().ok();

        Ok(Config {
            matrix_homeserver: env::var("MATRIX_HOMESERVER")?,
            matrix_username: env::var("MATRIX_USERNAME")?,
            matrix_password: env::var("MATRIX_PASSWORD")?,
            llm_api_url: env::var("LLM_API_URL")?,
            mqtt_broker: env::var("MQTT_BROKER")?,
            mqtt_port: env::var("MQTT_PORT")?.parse()?,
            mqtt_topic: env::var("MQTT_TOPIC")?,
        })
    }
}
