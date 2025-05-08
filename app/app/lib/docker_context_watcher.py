# app/docker_context_watcher.py
import asyncio
import json
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
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
        print(f"Error reading Docker config: {e}")
        return "default"


class DockerConfigEventHandler(FileSystemEventHandler):
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.queue = queue
        self.loop = loop

    def on_any_event(self, event):
        if event.dest_path == str(CONFIG_PATH) and event.event_type in ("moved",):
            logger.info(f"Detected event: {event.event_type} on {event.src_path}")
            asyncio.run_coroutine_threadsafe(self.queue.put(event), self.loop)


async def monitor_docker_context():
    queue = asyncio.Queue()
    last_context = get_current_context_from_config()

    loop = asyncio.get_event_loop()
    event_handler = DockerConfigEventHandler(queue, loop)
    observer = Observer()
    observer.schedule(event_handler, str(CONFIG_PATH.parent), recursive=False)
    observer.start()

    logger.info(f"Startup docker context watcher: {CONFIG_PATH}")
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
