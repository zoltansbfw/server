import asyncio
import websockets
import os

clients = set()

async def websocket_handler(ws):
    print("Client connected!")
    clients.add(ws)
    try:
        async for msg in ws:
            print("Received:", msg)
            await asyncio.gather(*[
                c.send(msg) for c in clients if c != ws
            ], return_exceptions=True)
    finally:
        clients.remove(ws)
        print("Client disconnected.")

async def connection_handler(reader, writer):
    # Read headers
    headers = []
    while True:
        line = await reader.readline()
        if not line:
            break
        decoded = line.decode().strip()
        if decoded == "":
            break
        headers.append(decoded)

    if not headers:
        writer.close()
        return

    request_line = headers[0]

    # ---- HEALTH CHECK ----
    if request_line.startswith("HEAD") or request_line.startswith("GET / ") and \
       not any("Upgrade: websocket" in h for h in headers):
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

    # ---- WEBSOCKET REQUEST ----
    if any("Upgrade: websocket" in h for h in headers):
        ws_server = websockets.server.ServerConnection(websocket_handler)
        await ws_server.handler(reader, writer)
        return

    # ---- UNKNOWN REQUEST: return OK ----
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
    PORT = int(os.environ.get("PORT", 10000))
    server = await asyncio.start_server(connection_handler, "0.0.0.0", PORT)
    print(f"Server running on port {PORT}")
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())

