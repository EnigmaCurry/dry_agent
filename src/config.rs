// src/config.rs
use anyhow::Result;
use dirs;
use serde::Deserialize;
use std::env;
use std::path::PathBuf;

#[derive(Debug, Deserialize, Clone)]
pub struct Config {
    pub matrix_homeserver: String,
    pub matrix_username: String,
    pub matrix_password: String,
    pub llm_api_url: String,
    pub mqtt_broker: String,
    pub mqtt_port: u16,
    pub mqtt_topic: String,
    pub mqtt_client_cert: String,
    pub mqtt_client_key: String,
    pub mqtt_ca_cert: String,
    pub matrix_store_path: PathBuf,
}

impl Config {
    pub fn from_env() -> Result<Self> {
        dotenv::dotenv().ok();

        // Get user's home directory and construct default store path
        let home_dir = dirs::home_dir().unwrap_or_else(|| PathBuf::from(".")); // Fallback to current dir if home not found
        let default_store_path = home_dir
            .join(".local")
            .join("dry_agent")
            .join("matrix_store");

        Ok(Config {
            matrix_homeserver: env::var("MATRIX_HOMESERVER")?,
            matrix_username: env::var("MATRIX_USERNAME")?,
            matrix_password: env::var("MATRIX_PASSWORD")?,
            llm_api_url: env::var("LLM_API_URL")?,
            mqtt_broker: env::var("MQTT_BROKER")?,
            mqtt_port: env::var("MQTT_PORT")?.parse()?,
            mqtt_topic: env::var("MQTT_TOPIC")?,
            mqtt_client_cert: env::var("MQTT_CLIENT_CERT")?,
            mqtt_client_key: env::var("MQTT_CLIENT_KEY")?,
            mqtt_ca_cert: env::var("MQTT_CA_CERT")?,
            matrix_store_path: env::var("MATRIX_STORE_PATH")
                .map(PathBuf::from)
                .unwrap_or(default_store_path),
        })
    }
}
