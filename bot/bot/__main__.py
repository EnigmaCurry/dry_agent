from .bot import BotHandler
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    try:
        asyncio.run(BotHandler().run())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
