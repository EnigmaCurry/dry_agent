mod bot;
mod config;
mod llm;
mod models;
mod mqtt;
use anyhow::Result;
use std::fs::{File, OpenOptions};
use std::io::{Error, ErrorKind, Write};

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    env_logger::init();

    // Check for other instances using lock file
    let _lock = match acquire_lock() {
        Ok(lock) => lock,
        Err(e) => {
            eprintln!("Error: {}", e);
            eprintln!("Another instance of dry_agent is already running.");
            std::process::exit(1);
        }
    };

    // Load configuration
    let config = config::Config::from_env()?;

    // Create and start the bot
    let bot = bot::Bot::new(config).await?;
    bot.login().await?;

    // Display verification status
    bot.display_verification_status().await?;

    // Start the bot in a background task
    let bot_clone = bot.clone();
    let sync_task = tokio::spawn(async move {
        if let Err(e) = bot_clone.start().await {
            eprintln!("Bot error: {}", e);
        }
    });

    // Wait for Ctrl+C
    tokio::signal::ctrl_c().await?;
    println!("Shutting down...");

    // Abort the sync task
    sync_task.abort();

    Ok(())
}

fn acquire_lock() -> Result<File, Error> {
    let lock_path = "/tmp/dry_agent.lock";

    // Try to open the lock file exclusively
    match OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(lock_path)
    {
        Ok(mut file) => {
            // Write PID to lock file
            let pid = std::process::id();
            writeln!(file, "{}", pid)?;
            Ok(file)
        }
        Err(e) => {
            if e.kind() == ErrorKind::AlreadyExists {
                // Check if the process is still running
                if let Ok(content) = std::fs::read_to_string(lock_path) {
                    if let Ok(pid) = content.trim().parse::<u32>() {
                        // Check if process is still running
                        #[cfg(unix)]
                        {
                            let status = std::process::Command::new("kill")
                                .arg("-0")
                                .arg(pid.to_string())
                                .stdout(std::process::Stdio::null())
                                .stderr(std::process::Stdio::null())
                                .status();

                            if status.is_ok() && status.unwrap().success() {
                                return Err(Error::new(
                                    ErrorKind::AlreadyExists,
                                    format!("Another instance is already running with PID {}", pid),
                                ));
                            }
                        }

                        // Process not running, remove stale lock file
                        std::fs::remove_file(lock_path)?;
                        return acquire_lock(); // Try again
                    }
                }

                // Invalid lock file, remove it
                std::fs::remove_file(lock_path)?;
                return acquire_lock(); // Try again
            }
            Err(e)
        }
    }
}
