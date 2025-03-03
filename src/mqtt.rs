use anyhow::{Context, Result};
use paho_mqtt as mqtt;
use std::fs;
use std::time::Duration;

use crate::models::MqttActionMessage;

pub struct MqttClient {
    client: mqtt::Client,
    topic: String,
}

impl MqttClient {
    pub fn new(
        broker: String,
        port: u16,
        client_id: &str,
        topic: String,
        client_cert_path: String,
        key_path: String,
        ca_cert_path: String,
    ) -> Result<Self> {
        // Get absolute paths to ensure files can be found
        let client_cert_path = fs::canonicalize(&client_cert_path).context(format!(
            "Failed to find client certificate file: {}",
            client_cert_path
        ))?;
        let key_path = fs::canonicalize(&key_path)
            .context(format!("Failed to find key file: {}", key_path))?;
        let ca_cert_path = fs::canonicalize(&ca_cert_path).context(format!(
            "Failed to find CA certificate file: {}",
            ca_cert_path
        ))?;

        println!("Using client certificate: {:?}", client_cert_path);
        println!("Using CA certificate: {:?}", ca_cert_path);
        println!("Using key: {:?}", key_path);

        // Create the connection URI
        let uri = format!("ssl://{}:{}", broker, port);
        println!("Connecting to MQTT broker at: {}", uri);

        // Create MQTT client options
        let create_opts = mqtt::CreateOptionsBuilder::new()
            .server_uri(uri)
            .client_id(client_id)
            .finalize();

        // Create the client
        let client = mqtt::Client::new(create_opts)?;

        // Set up SSL options with full verification
        let ssl_opts = mqtt::SslOptionsBuilder::new()
            .trust_store(ca_cert_path.as_path())
            .context("Failed to set trust_store")?
            .key_store(client_cert_path.as_path())
            .context("Failed to set key_store")?
            .private_key(key_path.as_path())
            .context("Failed to set private_key")?
            .enable_server_cert_auth(true)
            .verify(true)
            .finalize();

        // Set up connection options
        let conn_opts = mqtt::ConnectOptionsBuilder::new()
            .ssl_options(ssl_opts)
            .keep_alive_interval(Duration::from_secs(20))
            .clean_session(true)
            .finalize();

        // Connect with full certificate validation
        client
            .connect(conn_opts)
            .context("Failed to connect to MQTT broker with certificate validation")?;

        println!("Connected to MQTT broker successfully with full certificate validation!");

        // Subscribe to a topic if needed
        client
            .subscribe(&format!("{}/response", topic), 1)
            .context("Failed to subscribe to response topic")?;

        // Set up message handling
        let rx = client.start_consuming();

        // Start a thread to handle incoming messages
        std::thread::spawn(move || {
            for msg in rx.iter() {
                if let Some(msg) = msg {
                    println!(
                        "Received MQTT message: topic={}, payload={:?}",
                        msg.topic(),
                        String::from_utf8_lossy(msg.payload())
                    );
                }
            }
        });

        Ok(Self { client, topic })
    }

    pub fn send_action(&mut self, action: MqttActionMessage) -> Result<()> {
        let payload = serde_json::to_string(&action)?;

        println!("Sending MQTT message to topic {}: {}", self.topic, payload);

        let msg = mqtt::Message::new(
            &self.topic,
            payload,
            1, // QoS level: At least once
        );

        self.client.publish(msg)?;
        Ok(())
    }
}
