import asyncio
import os
import json
from datetime import datetime

# Import the recommended way to start the WebSocket server
# from the websockets library, avoiding the DeprecationWarning.
from websockets.server import serve 
from websockets import exceptions as ws_exceptions

# --- Global State ---
clients = set()
# Store the last 20 messages for history persistence
history = []
MAX_HISTORY = 20

# --- Helper Functions ---

# Creates a structured message dictionary (to be sent as JSON)
def create_message(username, text, is_system=False):
    return {
        "timestamp": datetime.now().isoformat(),
        "username": "SYSTEM" if is_system else username,
        "text": text,
        "is_system": is_system
    }

# Prepares the history for a new client
async def send_history(websocket):
    if history:
        # Send the history as one large JSON object array
        await websocket.send(json.dumps({
            "type": "history",
            "messages": history
        }))

# Broadcasts a message object to all connected clients
async def broadcast_message(msg_obj):
    broadcast_json = json.dumps({
        "type": "message",
        "data": msg_obj
    })
    
    # Use asyncio.gather to send the message concurrently to all clients
    await asyncio.gather(*[
        client.send(broadcast_json) 
        for client in clients
    ])

# --- Main WebSocket Handler ---

async def websocket_handler(websocket):
    # 1. INITIAL HANDSHAKE: Get Username 
    username = "Anonymous"
    try:
        # The client must send their username as the first message
        initial_message = json.loads(await websocket.recv())
        username = initial_message.get("username", "Anonymous").strip()
        if not username:
             username = "Anonymous"
        
    except (json.JSONDecodeError, ws_exceptions.ConnectionClosedOK, TypeError):
        # If the client fails the handshake, close the connection
        print("Connection closed: Invalid initial handshake.")
        return
    
    # Store the client's username with the connection object
    websocket.username = username 
    clients.add(websocket)
    print(f"Client '{username}' connected. Total clients: {len(clients)}")

    # 2. SEND HISTORY and WELCOME
    await send_history(websocket)
    
    # Notify everyone that a new user joined (System Message)
    welcome_msg = create_message(username, f"{username} has joined the chat.", is_system=True)
    history.append(welcome_msg)
    if len(history) > MAX_HISTORY:
        history.pop(0)
    await broadcast_message(welcome_msg)
    
    # 3. Handle incoming messages
    try:
        async for message_json in websocket:
            try:
                data = json.loads(message_json)
                text = data.get("text", "").strip()
                
                if text:
                    # Create the structured message object
                    msg_obj = create_message(username, text)
                    
                    # Update history
                    history.append(msg_obj)
                    if len(history) > MAX_HISTORY:
                        history.pop(0)
                        
                    # Broadcast to all clients
                    await broadcast_message(msg_obj)

            except json.JSONDecodeError:
                print(f"Received invalid JSON from {username}")
                
    except ws_exceptions.ConnectionClosedOK:
        pass # Client closed the connection normally
    except Exception as e:
        print(f"An unexpected error occurred for {username}: {e}")
        
    finally:
        # 4. Cleanup on disconnect
        clients.remove(websocket)
        print(f"Client '{username}' disconnected. Total clients: {len(clients)}")
        
        # Notify everyone that the user left (System Message)
        leave_msg = create_message(username, f"{username} has left the chat.", is_system=True)
        history.append(leave_msg)
        if len(history) > MAX_HISTORY:
            history.pop(0)
        await broadcast_message(leave_msg)


# --- Server Startup ---

async def main():
    # Use the PORT environment variable provided by Render or default to 8080
    PORT = int(os.environ.get("PORT", 8080))
    HOST = "0.0.0.0" 
    
    print(f"Starting WebSocket server on ws://{HOST}:{PORT}")

    # Use the websockets.serve entry point for a standard, robust server
    # This replaces all the complex manual connection_handler logic
    async with serve(websocket_handler, HOST, PORT):
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped manually.")
