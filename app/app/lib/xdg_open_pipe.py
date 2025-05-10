import os
from app.broadcast import broadcast
from app.models.events import OpenURLEvent
import asyncio

PIPE_PATH = "/tmp/xdg_open_pipe"


async def watch_xdg_open_pipe():
    os.makedirs(os.path.dirname(PIPE_PATH), exist_ok=True)
    if not os.path.exists(PIPE_PATH):
        os.mkfifo(PIPE_PATH)
    loop = asyncio.get_running_loop()  # capture main loop

    def blocking_watch():
        with open(PIPE_PATH, "r") as pipe:
            while True:
                url = pipe.readline().strip()
                if url:
                    loop.call_soon_threadsafe(
                        asyncio.create_task, broadcast(OpenURLEvent(url=url))
                    )

    await asyncio.to_thread(blocking_watch)
