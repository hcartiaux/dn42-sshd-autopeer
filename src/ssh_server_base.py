import logging
import paramiko
import socket
import threading
from abc import ABC, abstractmethod
from sys import platform


class SSHServerBase(ABC):
    """
    Abstract base class for creating a multi-threaded SSH server.

    Provides a framework for setting up an SSH server with configurable
    connection handling.

    Attributes:
        _is_running (threading.Event): Thread-safe flag to control server running state.
        _socket (socket.socket): Socket used for listening to incoming connections.
        _listen_thread (threading.Thread): Thread responsible for handling incoming connections.
    """

    def __init__(self, server_interface):
        """
        Initialize the SSH server base infrastructure.

        Parameters:
            server_interface: The paramiko server interface to handle SSH connections
                              and the authentication.
        """
        self._server = server_interface()
        self._is_running = threading.Event()
        self._socket = None
        self._listen_thread = None

    def start(self, address='::1', port=22, timeout=1):
        """
        Start the SSH server and begin listening for incoming connections.

        Sets up an IPv6 socket, configures socket options, and starts
        a listening thread.

        Parameters:
            address (str, optional): IPv6 address to bind the server. Defaults to '::1'.
            port (int, optional): Port number to listen on. Defaults to 22.
            timeout (float, optional): Socket connection timeout. Defaults to 1 second.
        """
        if not self._is_running.is_set():
            self._is_running.set()
            self._socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)

            # reuse port is not available on windows
            if platform == "linux" or platform == "linux2":
                self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, True)

            self._socket.settimeout(timeout)
            self._socket.bind((address, port))

            self._listen_thread = threading.Thread(target=self._listen)
            self._listen_thread.start()

    def stop(self):
        """
        Gracefully stop the SSH server.

        Clears the running state, waits for the listening thread to complete,
        and closes the server socket.
        """
        if self._is_running.is_set():
            self._is_running.clear()
            self._listen_thread.join()
            self._socket.close()

    def _listen(self):
        """
        Continuously listen for and handle incoming SSH connections.

        Runs while the server is active, accepting client connections,
        establishing SSH transport, and spawning connection handling threads.
        """
        logging.info("[SSHServerBase] Listening thread started")
        while self._is_running.is_set():
            try:
                self._socket.listen()
                client, addr = self._socket.accept()
                logging.info(f"[SSHServerBase] Accepted connection from {addr}")

                # create the SSH transport object
                session = paramiko.Transport(client)
                session.add_server_key(self._host_key)

                # start the SSH server
                try:
                    session.start_server(server=self._server)
                except ConnectionResetError:
                    logging.error(f"[SSHServerBase] Connection reset by peer")
                    continue
                except paramiko.SSHException:
                    logging.exception(f"[SSHServerBase] SSHException in _listen()")
                    continue
                except:
                    logging.exception(f"[SSHServerBase] Unmanaged exception")
                    continue

                channel = session.accept()
                if channel is None:
                    logging.warning(f"[SSHServerBase] No channel request from {addr}")
                    session.close()
                    continue

                username = self._server.last_login
                thread = threading.Thread(target=self.connection_function,
                                          daemon=True,
                                          args=(client, session, channel, username))
                thread.start()
                logging.info(f"[SSHServerBase] Started thread {thread.ident} for {username}@{addr}")

            except socket.timeout:
                pass

    @abstractmethod
    def connection_function(self, client, session, channel, username):
        """
        Abstract method to handle individual SSH connections.

        Must be implemented by subclasses to define specific
        connection handling logic.

        Parameters:
            client (socket.socket): The connected client socket.
            session (paramiko.Transport): The SSH transport session.
            channel (paramiko.Channel): The SSH communication channel.
            username (str): The SSH username.
        """
        pass
