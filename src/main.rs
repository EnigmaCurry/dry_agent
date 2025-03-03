mod bot;
mod config;
mod llm;
mod models;
mod mqtt;

use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    //std::env::set_var("RUST_LOG", "debug,paho_mqtt=trace");
    env_logger::init();

    // Load configuration
    let config = config::Config::from_env()?;

    // Create and start the bot
    let bot = bot::Bot::new(config).await?;
    bot.login().await?;
    bot.start().await?;

    // This will keep running until interrupted
    tokio::signal::ctrl_c().await?;
    println!("Shutting down...");

    Ok(())
}
