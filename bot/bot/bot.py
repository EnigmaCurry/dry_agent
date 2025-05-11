import os
import sys
import asyncio
import logging
import sqlite3
from abc import ABC, abstractmethod
import requests

# Matrix imports
from nio import AsyncClient, InviteMemberEvent, MatrixRoom
from nio.events.room_events import RoomMessageText

# Discord imports
import discord
from discord import Intents
from discord.channel import DMChannel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database file path
DB_FILE = os.getenv("BOT_STATE_DB", "/data/bot_state.db")

# Parse allowed friend IDs
FRIENDS = os.getenv("BOT_FRIEND_IDS", "")
raw_friends = [f.strip() for f in FRIENDS.split(",") if f.strip()]
allowed_matrix = {f for f in raw_friends if f.startswith("@")}  # Matrix IDs
allowed_discord = {int(f) for f in raw_friends if f.isdigit()}  # Discord IDs

# Env vars
HOMESERVER = os.getenv("MATRIX_HOMESERVER", "").strip()
MATRIX_USER = os.getenv("MATRIX_USER", "").strip()
MATRIX_PASSWORD = os.getenv("MATRIX_PASSWORD", "").strip()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()


PUBLIC_HOST = os.getenv("PUBLIC_HOST", "127.0.0.1").strip()
PUBLIC_PORT = os.getenv("PUBLIC_PORT", "8123").strip()

# Client cert (and its key) for mTLS
CLIENT_CERT = (
    "/certs/dry-agent_Bot.crt",
    "/certs/dry-agent_Bot.key",
)
CA_BUNDLE = "/certs/dry-agent-root.crt"


# Feature flags
matrix_enabled = bool(HOMESERVER)
discord_enabled = bool(DISCORD_TOKEN)

# Validate Matrix config
if matrix_enabled and (not MATRIX_USER or not MATRIX_PASSWORD):
    logger.error("MATRIX_HOMESERVER set but MATRIX_USER/PASSWORD missing")
    matrix_enabled = False


async def noop():
    """Idle loop if no protocols are enabled"""
    logger.info("Entering idle loop. No chat protocols configured.")
    while True:
        await asyncio.sleep(3600)


class ChatPlatform(ABC):
    @abstractmethod
    async def send_message(self, room_id: str, text: str):
        pass

    @abstractmethod
    async def start(self):
        pass


class MatrixPlatform(ChatPlatform):
    def __init__(self, homeserver: str, user: str, password: str, handler):
        self.client = AsyncClient(homeserver, user)
        self.password = password
        self.handler = handler
        self.client.add_event_callback(self._on_invite, InviteMemberEvent)
        self.client.add_event_callback(self._on_message, RoomMessageText)

    async def login(self):
        resp = await self.client.login(self.password)
        if not getattr(resp, "access_token", None):
            raise RuntimeError(f"Matrix login failed: {resp}")
        logger.info("Matrix logged in as %s", self.client.user_id)

    async def _on_invite(self, room: MatrixRoom, event: InviteMemberEvent):
        # Automatically join one-to-one invites from allowed friends
        if event.membership != "invite":
            return
        if event.sender not in allowed_matrix:
            logger.info("Matrix invite from unauthorized user %s", event.sender)
            return
        if event.state_key != self.client.user_id:
            return
        logger.info("Joining room %s invited by %s", room.room_id, event.sender)
        join_resp = await self.client.join(room.room_id)
        logger.info("Matrix join response: %s", join_resp)

    async def _on_message(self, room: MatrixRoom, event: RoomMessageText):
        if event.sender not in allowed_matrix:
            return
        # pass event.event_id for dedupe
        await self.handler.handle_request(
            platform="matrix",
            room_id=room.room_id,
            sender=event.sender,
            content=event.body.strip(),
            message_id=event.event_id,
        )

    async def send_message(self, room_id: str, text: str):
        await self.client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": text},
        )

    async def start(self):
        await self.login()
        await self.client.sync_forever(timeout=30000)


class DiscordPlatform(ChatPlatform, discord.Client):
    def __init__(self, token: str, handler):
        intents = Intents.default()
        intents.messages = True
        super().__init__(intents=intents)
        discord.Client.__init__(self, intents=intents)
        self.token = token
        self.handler = handler

    async def on_ready(self):
        logger.info("Discord logged in as %s", self.user)

    async def on_message(self, message):
        # Only handle DMs from allowed friends
        if not isinstance(message.channel, DMChannel) or message.author.bot:
            return
        uid = message.author.id
        if uid not in allowed_discord:
            logger.info("Discord DM from unauthorized user %s", uid)
            return
        await self.handler.handle_request(
            platform="discord",
            room_id=message.channel.id,
            sender=uid,
            content=message.content.strip(),
            message_id=str(message.id),
        )

    async def send_message(self, room_id: str, text: str):
        channel = await self.fetch_channel(int(room_id))
        await channel.send(text)

    async def start(self):
        await super().start(self.token)


class BotHandler:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self._init_db()

    def _init_db(self):
        c = self.conn.cursor()
        c.execute(
            """
            CREATE TABLE IF NOT EXISTS responded (
                platform TEXT,
                message_id TEXT,
                PRIMARY KEY (platform, message_id)
            )
            """
        )
        self.conn.commit()

    def _has_responded(self, platform: str, message_id: str) -> bool:
        c = self.conn.cursor()
        c.execute(
            "SELECT 1 FROM responded WHERE platform = ? AND message_id = ?",
            (platform, message_id),
        )
        return c.fetchone() is not None

    def _record_response(self, platform: str, message_id: str):
        c = self.conn.cursor()
        c.execute(
            "INSERT OR IGNORE INTO responded (platform, message_id) VALUES (?, ?)",
            (platform, message_id),
        )
        self.conn.commit()

    async def handle_request(
        self, platform: str, room_id: str, sender: str, content: str, message_id: str
    ):
        logger.info("Handling request on %s from %s: %s", platform, sender, content)
        if self._has_responded(platform, message_id):
            return

        try:
            lower = content.lower()
            if "login" in lower or "log me in" or "log in" in lower:
                login_url = get_login_url()
                await self._send(platform, room_id, login_url)
            else:
                logger.info("No known command in message; ignoring")
            # You might add more command logic here
        except Exception as e:
            err_msg = f"❌ Error processing your request: {e}"
            logger.error(err_msg)
            await self._send(platform, room_id, err_msg)
        finally:
            # Always record it to prevent reprocessing
            self._record_response(platform, message_id)

    async def _send(self, platform: str, room_id: str, text: str):
        if platform == "matrix":
            await self.matrix.send_message(room_id, text)
        elif platform == "discord":
            await self.discord.send_message(room_id, text)

    async def run(self):
        tasks = []

        if matrix_enabled:
            self.matrix = MatrixPlatform(HOMESERVER, MATRIX_USER, MATRIX_PASSWORD, self)
            tasks.append(self._wrap_task(self.matrix.start(), "Matrix"))

        if discord_enabled:
            self.discord = DiscordPlatform(DISCORD_TOKEN, self)
            tasks.append(self._wrap_task(self.discord.start(), "Discord"))

        if not tasks:
            tasks.append(noop())

        await asyncio.gather(*tasks)

    async def _wrap_task(self, coro, name):
        try:
            await coro
        except Exception as e:
            logger.exception(f"{name} task crashed: {e}")


def get_login_url() -> str:
    try:
        response = requests.post(
            "https://127.0.0.1:8001/admin/generate-auth-token",
            cert=CLIENT_CERT,
            verify=CA_BUNDLE,
            timeout=5,
        )
        response.raise_for_status()
    except Exception as e:
        logger.exception("Failed to generate auth token")
        raise RuntimeError("Failed to generate auth token") from e

    try:
        response = requests.get(
            "https://127.0.0.1:8001/admin/get-login-url",
            cert=CLIENT_CERT,
            verify=CA_BUNDLE,
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        if "login_url" not in data:
            raise ValueError("Missing login_url in server response")
        return data["login_url"]
    except Exception as e:
        logger.exception("Failed to retrieve login URL")
        raise RuntimeError("Failed to retrieve login URL") from e
