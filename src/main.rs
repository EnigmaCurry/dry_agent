mod bot;
mod config;
mod llm;
mod models;
mod mqtt;

use anyhow::Result;

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging with more verbose output
    std::env::set_var("RUST_LOG", "info,matrix_sdk=debug,dry_agent=trace");
    env_logger::init();

    // Load configuration
    let config = config::Config::from_env()?;

    // Create and start the bot
    let bot = bot::Bot::new(config).await?;
    bot.login().await?;

    println!("Bot started and logged in, now starting event handlers...");

    // This will set up the event handlers
    bot.start().await?;

    // This part should never be reached as sync() will run forever
    println!("Sync ended - this message should not appear under normal circumstances");

    Ok(())
}
