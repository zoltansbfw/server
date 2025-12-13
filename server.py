import os
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import uvicorn

app = FastAPI()


class ChatServer:
    def __init__(self):
        self.active_connections: dict[WebSocket, str] = {}
        self.message_history: list[str] = []

    async def connect(self, websocket: WebSocket, username: str):
        await websocket.accept()
        self.active_connections[websocket] = username

        # Send chat history to the new user
        for message in self.message_history:
            await websocket.send_text(message)

        # Announce join (bold)
        timestamp = self._timestamp()
        join_msg = f"<b>[{timestamp}] {username} joined the chat</b>"
        self.message_history.append(join_msg)
        await self.broadcast(join_msg)

    def disconnect(self, websocket: WebSocket):
        username = self.active_connections.get(websocket, "Unknown")
        self.active_connections.pop(websocket, None)

        timestamp = self._timestamp()
        leave_msg = f"<b>[{timestamp}] {username} left the chat</b>"
        self.message_history.append(leave_msg)
        return leave_msg

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

    @staticmethod
    def _timestamp():
        return datetime.now().strftime("%H:%M")


chat_server = ChatServer()


def handle_command(command: str, username: str):
    cmd = command.lower().strip()

    if cmd == "/help":
        return (
            "[Commands]\n"
            "/help  - show this message\n"
            "/users - list online users\n"
            "/clear - clear chat (admin only)"
        )

    if cmd == "/users":
        users = ", ".join(chat_server.active_connections.values())
        return f"[Users online] {users}"

    if cmd == "/clear":
        if username != "admin":
            return "Only admin can clear the chat."
        chat_server.message_history.clear()
        return "<b>Chat was cleared by admin</b>"

    return "Unknown command. Type /help"


@app.get("/")
async def health_check():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    username = websocket.query_params.get("username", "Anonymous")
    await chat_server.connect(websocket, username)

    try:
        while True:
            msg = await websocket.receive_text()

            # Commands
            if msg.startswith("/"):
                response = handle_command(msg, username)
                if response:
                    await websocket.send_text(response)
                continue

            timestamp = chat_server._timestamp()
            full_msg = f"[{timestamp}] {username}: {msg}"

            chat_server.message_history.append(full_msg)
            await chat_server.broadcast(full_msg)

    except WebSocketDisconnect:
        leave_msg = chat_server.disconnect(websocket)
        await chat_server.broadcast(leave_msg)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
