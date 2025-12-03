import asyncio
import websockets
import os

clients = set()

async def websocket_handler(ws):
    clients.add(ws)
    try:
        async for msg in ws:
            # broadcast to every other client
            await asyncio.gather(*[
                c.send(msg) for c in clients if c != ws
            ], return_exceptions=True)
    finally:
        clients.remove(ws)


async def connection_handler(reader, writer):
    request_line = await reader.readline()
    line = request_line.decode().strip()

    # Render health check (GET / or HEAD /)
    if line.startswith("HEAD") or (line.startswith("GET") and "Upgrade: websocket" not in line):
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
        return

    # Otherwise handle WebSocket upgrade
    ws_server = websockets.server.ServerConnection(websocket_handler)
    await ws_server.handler(reader, writer)


async def main():
    PORT = int(os.environ.get("PORT", 10000))
    server = await asyncio.start_server(connection_handler, "0.0.0.0", PORT)
    print(f"Server running on port {PORT}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
