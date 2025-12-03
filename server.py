import asyncio
import websockets
import os
import signal

# Set of connected clients
clients = set()

async def register(websocket):
    """Registers a client connection."""
    clients.add(websocket)
    print(f"Client connected. Total clients: {len(clients)}")

async def unregister(websocket):
    """Unregisters a client connection."""
    clients.remove(websocket)
    print(f"Client disconnected. Total clients: {len(clients)}")

async def consumer_handler(websocket):
    """Handles messages received from a client and broadcasts them."""
    async for message in websocket:
        # Broadcast the message to all other connected clients
        await asyncio.gather(*[
            client.send(message) for client in clients if client != websocket
        ], return_exceptions=True)

async def handler(websocket):
    """Main handler that manages connection lifecycle."""
    await register(websocket)
    try:
        await consumer_handler(websocket)
    finally:
        await unregister(websocket)

async def main():
    PORT = int(os.environ.get("PORT", 10000))
    # 'ws://0.0.0.0:{PORT}'
    
    # Corrected usage: serve is directly under the websockets module
    async with websockets.serve(handler, "0.0.0.0", PORT):
        print(f"Server running on port {PORT}")
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    # Corrected usage: Use asyncio.run() to manage the event loop
    asyncio.run(main())
