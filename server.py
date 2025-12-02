import asyncio
import websockets
import os

clients = set()

async def handle_ws(ws):
    clients.add(ws)
    try:
        async for message in ws:
            # Broadcast to everyone except sender
            await asyncio.gather(*[
                c.send(message) for c in clients if c != ws
            ])
    finally:
        clients.remove(ws)

# Handle HTTP requests (Render health checks)
async def process_request(path, request_headers):
    method = request_headers.get("Method", "")

    # Render sends HEAD and GET / for health checks
    if "Upgrade" not in request_headers:
        body = b"OK"
        return (
            200,
            [
                ("Content-Type", "text/plain"),
                ("Content-Length", str(len(body)))
            ],
            body
        )

    # Otherwise continue to WebSocket handshake
    return None

async def main():
    PORT = int(os.environ.get("PORT", 10000))

    print(f"Starting server on port {PORT}...")

    async with websockets.serve(
        handle_ws,
        "0.0.0.0",
        PORT,
        process_request=process_request
    ):
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
