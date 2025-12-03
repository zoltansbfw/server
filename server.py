import asyncio
import websockets
import os

clients = set()

async def handle(ws, path):
    print("Client connected")
    clients.add(ws)
    try:
        async for msg in ws:
            for client in clients:
                if client != ws:
                    await client.send(msg)
    except websockets.ConnectionClosed:
        pass
    finally:
        clients.remove(ws)
        print("Client disconnected")

async def main():
    PORT = int(os.environ.get("PORT", 10000))
    print(f"Starting WebSocket server on port {PORT}...")
    async with websockets.serve(handle, "0.0.0.0", PORT):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
