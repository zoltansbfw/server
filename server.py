import socket
import selectors


class ChatServer:
    def __init__(self, host, port):
        """Initialise the server attributes."""
        self._host = host
        self._port = port
        self._socket = None

        # Selector for sockets we read from
        self._read_selector = selectors.DefaultSelector()

        # Selector for sockets we write to (clients only)
        self._write_selector = selectors.DefaultSelector()

    def _init_server(self):
        """Initialises the server socket."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self._host, self._port))
        self._socket.listen()

        # Register server socket to accept new connections
        self._read_selector.register(
            self._socket,
            selectors.EVENT_READ,
            self._accept_connection,
        )

        print(f"Server listening on {self._host}:{self._port}")

    def _accept_connection(self, sock):
        """Accept a new client connection."""
        client, addr = sock.accept()
        print(f"Client connected from {addr}")

        # Register client for reading messages
        self._read_selector.register(
            client,
            selectors.EVENT_READ,
            self._receive_message,
        )

        # Register client for writing (broadcasting)
        self._write_selector.register(
            client,
            selectors.EVENT_WRITE,
        )

    def _receive_message(self, sock):
        """Receive a message from a client and broadcast it."""
        try:
            msg = sock.recv(1024)
        except ConnectionResetError:
            msg = b""

        # Client disconnected
        if not msg:
            print("Client disconnected")
            self._cleanup_client(sock)
            return

        print(msg.decode("utf8"))

        # Broadcast message to all other clients
        for key, _ in self._write_selector.select(0):
            client_sock = key.fileobj
            if client_sock is not sock:
                try:
                    client_sock.send(msg)
                except BrokenPipeError:
                    self._cleanup_client(client_sock)

    def _cleanup_client(self, sock):
        """Remove a disconnected client."""
        try:
            self._read_selector.unregister(sock)
        except Exception:
            pass

        try:
            self._write_selector.unregister(sock)
        except Exception:
            pass

        sock.close()

    def run(self):
        """Starts the server and runs indefinitely."""
        self._init_server()
        print("Running server...")

        while True:
            for key, _ in self._read_selector.select():
                callback = key.data
                callback(key.fileobj)


if __name__ == "__main__":
    # IMPORTANT for Render:
    # host must be 0.0.0.0, not localhost
    server = ChatServer("0.0.0.0", 7342)
    server.run()
