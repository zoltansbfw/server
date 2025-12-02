# server.py
import asyncio
import json
import os
import sqlite3
from datetime import datetime, timezone

import websockets
from websockets.exceptions import ConnectionClosedOK, ConnectionClosedError

DB_PATH = "messages.db"
HISTORY_LIMIT = 100  # number of messages to send to newly connected clients

clients = set()                # set of connected websocket objects
usernames = dict()             # websocket -> username
db_lock = asyncio.Lock()       # guard sqlite access for thread-safety in asyncio

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        text TEXT NOT NULL,
        ts TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

async def save_message(username: str, text: str, ts: str):
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO messages (username, text, ts) VALUES (?, ?, ?)", (username, text, ts))
        conn.commit()
        conn.close()

async def load_history(limit=HISTORY_LIMIT):
    async with db_lock:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT username, text, ts FROM messages ORDER BY id DESC LIMIT ?", (limit,))
        rows = c.fetchall()
        conn.close()
    # rows are newest-first, convert to oldest-first
    rows.reverse()
    return [{"user": r[0], "text": r[1], "ts": r[2]} for r in rows]

async def broadcast(obj, exclude_ws=None):
    """Broadcast a Python object (will JSON-serialize) to all clients except exclude_ws."""
    if not clients:
        return
    msg = json.dumps(obj)
    to_send = [c.send(msg) for c in clients if c != exclude_ws]
    if to_send:
        await asyncio.gather(*to_send, return_exceptions=True)

async def handle(ws):
    # register
    clients.add(ws)
    try:
        # Send history to the newly connected client
        history = await load_history()
        await ws.send(json.dumps({"type": "history", "messages": history}))

        async for raw in ws:
            try:
                data = json.loads(raw)
            except Exception:
                # ignore malformed messages
                continue

            typ = data.get("type")

            if typ == "join":
                # user announces their username
                username = data.get("user", "Anonymous")[:32]
                usernames[ws] = username
                # notify others
                await broadcast({
                    "type": "system",
                    "text": f"{username} joined the chat.",
                    "ts": datetime.now(timezone.utc).isoformat()
                }, exclude_ws=ws)
            elif typ == "message":
                username = usernames.get(ws, "Anonymous")
                text = data.get("text", "")
                if not text:
                    continue
                ts = datetime.now(timezone.utc).isoformat()
                # save to DB
                await save_message(username, text, ts)
                # broadcast actual message to everyone (including sender)
                msg_obj = {
                    "type": "message",
                    "user": username,
                    "text": text,
                    "ts": ts
                }
                # include sender as well
                await broadcast(msg_obj, exclude_ws=None)
            else:
                # ignore unknown types (could extend with typing, reactions, etc.)
                continue

    except (ConnectionClosedOK, ConnectionClosedError):
        pass
    finally:
        # cleanup on disconnect
        clients.discard(ws)
        left_user = usernames.pop(ws, None)
        if left_user:
            await broadcast({
                "type": "system",
                "text": f"{left_user} left the chat.",
                "ts": datetime.now(timezone.utc).isoformat()
            }, exclude_ws=None)

async def main():
    init_db()
    port = int(os.environ.get("PORT", 6789))
    host = "0.0.0.0"
    async with websockets.serve(handle, host, port):
        print(f"Server running on ws://{host}:{port}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
