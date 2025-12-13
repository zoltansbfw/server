import os
import re
import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()


class ChatServer:
    def __init__(self, name: str):
        self.name = name
        self.active_connections: dict[WebSocket, str] = {}
        self.message_history: list[str] = []

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[websocket] = username

        # Send chat history to the new user
        for message in self.message_history:
            await websocket.send_text(message)

        # Announce join
        timestamp = self._timestamp()
        join_msg = f"<b>[{timestamp}] {username} joined #{self.name}</b>"
        self.message_history.append(join_msg)
        await self.broadcast(join_msg)

    def disconnect(self, websocket: WebSocket):
        username = self.active_connections.get(websocket, "Unknown")
        self.active_connections.pop(websocket, None)

        timestamp = self._timestamp()
        leave_msg = f"<b>[{timestamp}] {username} left #{self.name}</b>"
        self.message_history.append(leave_msg)
        return leave_msg

    async def broadcast(self, message: str):
        for connection in list(self.active_connections.keys()):
            try:
                await connection.send_text(message)
            except Exception:
                # drop broken connections
                self.active_connections.pop(connection, None)

    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%H:%M")


# --- Channels registry ---
channels: dict[str, ChatServer] = {}


def get_channel(name: str) -> ChatServer:
    if name not in channels:
        channels[name] = ChatServer(name)
    return channels[name]


# --- Message formatter ---
def format_message(msg: str) -> str:
    msg = re.sub(r"\*\*(.*?)\*\*", r"<b>\1</b>", msg)   # Bold
    msg = re.sub(r"\*(.*?)\*", r"<i>\1</i>", msg)       # Italic
    msg = re.sub(r"__(.*?)__", r"<u>\1</u>", msg)       # Underline
    msg = re.sub(r"~~(.*?)~~", r"<s>\1</s>", msg)       # Strikethrough
    msg = re.sub(r"`(.*?)`", r"<code>\1</code>", msg)   # Inline code
    return msg


# --- Commands ---
def handle_command(command: str, username: str, channel: ChatServer):
    cmd = command.lower().strip()

    if cmd == "/help":
        return (
            "[Commands]\n"
            "/help  - show this message\n"
            "/users - list online users\n"
            "/clear - clear chat (admin only)"
        )

    if cmd == "/users":
        users = ", ".join(channel.active_connections.values())
        return f"[Users online in #{channel.name}] {users}"

    if cmd == "/clear":
        if username != "admin":
            return "Only admin can clear the chat."
        channel.message_history.clear()
        return f"<b>Chat in #{channel.name} was cleared by admin</b>"

    return "Unknown command. Type /help"


@app.get("/")
async def health_check():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    username = websocket.query_params.get("username", "Anonymous")
    channel_name = websocket.query_params.get("channel", "general")
    channel = get_channel(channel_name)

    await channel.connect(websocket, username)

    try:
        while True:
            msg = await websocket.receive_text()

            # Commands
            if msg.startswith("/"):
                response = handle_command(msg, username, channel)
                if response:
                    await websocket.send_text(response)
                continue

            # Apply formatting
            styled_msg = format_message(msg)

            timestamp = channel._timestamp()
            full_msg = f"[{timestamp}] {username}: {styled_msg}"

            channel.message_history.append(full_msg)
            await channel.broadcast(full_msg)

    except WebSocketDisconnect:
        leave_msg = channel.disconnect(websocket)
        await channel.broadcast(leave_msg)


# --- Auto clear every hour ---
@app.on_event("startup")
async def clear_task():
    async def clear_loop():
        while True:
            await asyncio.sleep(3600)  # 1 hour
            for channel in channels.values():
                channel.message_history.clear()
                await channel.broadcast("<b>Chat was automatically cleared</b>")
    asyncio.create_task(clear_loop())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
