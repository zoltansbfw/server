import asyncio
import websockets

clients = set()

async def handle(ws):
    clients.add(ws)
    try:
        async for msg in ws:
            await asyncio.gather(*[
                c.send(msg) for c in clients if c != ws
            ])
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        clients.remove(ws)

async def main():
    import asyncio
import websockets
import os

clients = set()

async def handle_ws(ws):
    clients.add(ws)
    try:
        async for msg in ws:
            await asyncio.gather(*[
                c.send(msg) for c in clients if c != ws
            ])
    finally:
        clients.remove(ws)

# NEW: HTTP handler for Render health checks
async def handle_http(reader, writer):
    response = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/plain\r\n"
        "Content-Length: 2\r\n"
        "\r\n"
        "OK"
    )
    writer.write(response.encode())
    await writer.drain()
    writer.close()

async def main():
    PORT = int(os.environ.get("PORT", 6789))

    # Start WebSocket server
    ws_server = websockets.serve(handle_ws, "0.0.0.0", PORT)

    # Start HTTP health check server
    http_server = asyncio.start_server(handle_http, "0.0.0.0", PORT)

    print(f"Running on port {PORT}...")

    await asyncio.gather(ws_server, http_server)

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":

    asyncio.run(main())
