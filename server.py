import asyncio
import websockets
import os
import json
import sqlite3
from datetime import datetime

DB = "chat.db"

# --------------------------- DATABASE SETUP ---------------------------

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            text TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_message(username, text, timestamp):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("INSERT INTO messages (username, text, timestamp) VALUES (?, ?, ?)",
              (username, text, timestamp))
    conn.commit()
    conn.close()

def load_messages(limit=50):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT username, text, timestamp FROM messages ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    rows.reverse()
    return rows

# --------------------------- CHAT SERVER ---------------------------

clients = set()

async def broadcast(obj, exclude=None):
    message = json.dumps(obj)
    await asyncio.gather(
        *(c.send(message) for c in clients if c != exclude),
        return_exceptions=True
    )

async def handle(ws):
    clients.add(ws)

    # Send last 50 messages on connect
    history = load_messages()
    await ws.send(json.dumps({"type": "history", "messages": history}))

    try:
        async for msg in ws:
            data = json.loads(msg)

            username = data.get("username")
            text = data.get("text")
            timestamp = datetime.utcnow().isoformat()

            # Save message
            save_message(username, text, timestamp)

            # Broadcast to others
            await broadcast({
                "type": "message",
                "username": username,
                "text": text,
                "timestamp": timestamp
            }, exclude=ws)

    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.remove(ws)

# --------------------------- SERVER BOOT ---------------------------

async def main():
    init_db()

    PORT = int(os.environ.get("PORT", 10000))
    print(f"WebSocket server starting on port {PORT}")

    async with websockets.serve(
        handle,
        "0.0.0.0",
        PORT,
        ping_interval=20,
        ping_timeout=20
    ):
        await asyncio.Future()  # keep alive

if __name__ == "__main__":
    asyncio.run(main())
