use anyhow::Result;
use rumqttc::{Client, MqttOptions, QoS};
use std::time::Duration;
use tokio::task;

use crate::models::MqttActionMessage;

pub struct MqttClient {
    client: Client,
    topic: String,
}

impl MqttClient {
    pub fn new(broker: String, port: u16, client_id: &str, topic: String) -> Result<Self> {
        let mut mqtt_options = MqttOptions::new(client_id, broker, port);
        mqtt_options.set_keep_alive(Duration::from_secs(5));

        let (client, mut connection) = Client::new(mqtt_options, 10);

        // Start the MQTT connection handler in a separate task
        task::spawn(async move {
            loop {
                // No .await here - recv() is not async
                match connection.recv() {
                    Ok(notification) => {
                        println!("MQTT notification: {:?}", notification);
                    }
                    Err(e) => {
                        eprintln!("MQTT connection error: {:?}", e);
                        // Depending on the error, you might want to break or continue
                        break;
                    }
                }
            }
        });

        Ok(Self { client, topic })
    }

    pub fn send_action(&mut self, action: MqttActionMessage) -> Result<()> {
        let payload = serde_json::to_string(&action)?;
        self.client
            .publish(&self.topic, QoS::AtLeastOnce, false, payload)?;
        Ok(())
    }
}
