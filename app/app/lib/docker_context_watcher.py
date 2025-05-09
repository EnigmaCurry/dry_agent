# app/docker_context_watcher.py
import asyncio
import json
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileMovedEvent,
)
from app.broadcast import broadcast
from app.models.events import ContextChangedEvent
import logging

CONFIG_PATH = Path.home() / ".docker" / "config.json"

logger = logging.getLogger(__name__)


def get_current_context_from_config() -> str:
    try:
        with open(CONFIG_PATH) as f:
            data = json.load(f)
            return data.get("currentContext", "default")
    except Exception as e:
        logger.warning(f"Error reading Docker config: {e}")
        return "default"


class DockerConfigEventHandler(FileSystemEventHandler):
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.queue = queue
        self.loop = loop

    def dispatch(self, event):
        is_target = event.src_path == str(CONFIG_PATH) or getattr(
            event, "dest_path", None
        ) == str(CONFIG_PATH)
        if is_target and isinstance(
            event, (FileCreatedEvent, FileModifiedEvent, FileMovedEvent)
        ):
            logger.info(f"Detected event: {event.event_type} on {event.src_path}")
            asyncio.run_coroutine_threadsafe(self.queue.put(event), self.loop)


async def wait_for_config_file():
    if not CONFIG_PATH.exists():
        logger.info("Waiting for Docker config file to appear...")
    while not CONFIG_PATH.exists():
        await asyncio.sleep(1)
    logger.info("Docker config file found.")


async def monitor_docker_context():
    await wait_for_config_file()

    queue = asyncio.Queue()
    last_context = get_current_context_from_config()

    loop = asyncio.get_event_loop()
    event_handler = DockerConfigEventHandler(queue, loop)
    observer = Observer()
    observer.schedule(event_handler, str(CONFIG_PATH.parent), recursive=False)
    observer.start()

    logger.info(f"Started docker context watcher on: {CONFIG_PATH}")
    logger.info(f"Last context: {last_context}")
    try:
        while True:
            _ = await queue.get()
            current_context = get_current_context_from_config()
            logger.info(f"Current context: {current_context}")
            if current_context != last_context:
                last_context = current_context
                await broadcast(ContextChangedEvent(new_context=current_context))
    finally:
        observer.stop()
        observer.join()
