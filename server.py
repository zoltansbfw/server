import asyncio
import websockets
from websockets.server import serve
import os
import json
from datetime import datetime

# Global state
clients = set()
# Store the last 20 messages for history
history = []
MAX_HISTORY = 20

# Helper function to prepare a message object (Python dictionary)
def create_message(username, text):
    return {
        "timestamp": datetime.now().isoformat(),
        "username": username,
        "text": text,
    }

# Helper function to send the entire history to a single client
async def send_history(websocket):
    # Send the history as one large JSON array
    await websocket.send(json.dumps({
        "type": "history",
        "messages": history
    }))
    
async def websocket_handler(websocket):
    # 1. New Client: Get Username from the first message
    try:
        # The client must send their username first
        initial_message = json.loads(await websocket.recv())
        username = initial_message.get("username", "Anonymous")
        
    except (json.JSONDecodeError, websockets.exceptions.ConnectionClosedOK, TypeError):
        # Close connection if initial message is invalid
        return
        
    # Store the client's username with the connection
    websocket.username = username 
    clients.add(websocket)
    print(f"Client '{username}' connected. Total clients: {len(clients)}")

    # 2. Send History to the new client
    await send_history(websocket)
    
    try:
        # 3. Handle incoming messages
        async for message_json in websocket:
            try:
                data = json.loads(message_json)
                
                # Create the full message object
                msg_obj = create_message(username, data.get("text", ""))
                
                # Update history (Append and keep size capped)
                history.append(msg_obj)
                if len(history) > MAX_HISTORY:
                    history.pop(0)
                    
                # Broadcast the new message object to ALL clients
                broadcast_json = json.dumps({
                    "type": "message",
                    "data": msg_obj
                })
                
                await asyncio.gather(*[
                    client.send(broadcast_json) 
                    for client in clients
                ])

            except json.JSONDecodeError:
                print(f"Received invalid JSON from {username}")
                
    except websockets.exceptions.ConnectionClosedOK:
        pass
    except Exception as e:
        print(f"An unexpected error occurred for {username}: {e}")
    finally:
        # 4. Cleanup on disconnect
        clients.remove(websocket)
        print(f"Client '{username}' disconnected. Total clients: {len(clients)}")

async def main():
    PORT = int(os.environ.get("PORT", 8080))
    HOST = "0.0.0.0" 
    
    print(f"Starting WebSocket server on ws://{HOST}:{PORT}")
    async with serve(websocket_handler, HOST, PORT):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(main())
