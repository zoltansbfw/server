import os
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

        # Announce join
        join_msg = f"🟢 {username} joined the chat"
        self.message_history.append(join_msg)
        await self.broadcast(join_msg)

    def disconnect(self, websocket: WebSocket):
        username = self.active_connections.get(websocket, "Unknown")
        self.active_connections.pop(websocket, None)

        leave_msg = f"🔴 {username} left the chat"
        self.message_history.append(leave_msg)
        return leave_msg

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


chat_server = ChatServer()


@app.get("/")
async def health_check():
    return {"status": "ok"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Username passed as query param: /ws?username=John
    username = websocket.query_params.get("username", "Anonymous")

    await chat_server.connect(websocket, username)

    try:
        while True:
            msg = await websocket.receive_text()
            full_msg = f"{username}: {msg}"

            chat_server.message_history.append(full_msg)
            await chat_server.broadcast(full_msg)

    except WebSocketDisconnect:
        leave_msg = chat_server.disconnect(websocket)
        await chat_server.broadcast(leave_msg)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
