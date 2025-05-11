import os
import sys
import asyncio
import logging
import sqlite3
from abc import ABC, abstractmethod

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
        # dedupe by message_id
        if self._has_responded(platform, message_id):
            return
        lower = content.lower()
        if "login" in lower or "log me in" in lower:
            await self._send(platform, room_id, "TODO: give user link here")
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
            tasks.append(self.matrix.start())
        if discord_enabled:
            self.discord = DiscordPlatform(DISCORD_TOKEN, self)
            tasks.append(self.discord.start())
        if not tasks:
            tasks.append(noop())
        await asyncio.gather(*tasks)
