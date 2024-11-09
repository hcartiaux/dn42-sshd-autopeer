#!/usr/bin/env python

import paramiko
import os
import pty
import socket
import threading
import subprocess
import select

# Custom server interface that accepts any authentication attempt
class NoAuthSSHServer(paramiko.ServerInterface):
    def check_auth_none(self, username):
        return paramiko.AUTH_SUCCESSFUL  # Always accept password

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def check_channel_shell_request(self, channel):
        return True

def handle_client(client_socket):
    # Use Paramiko to handle SSH client connections
    transport = paramiko.Transport(client_socket)

    host_key = paramiko.RSAKey(filename='ssh-keys/ssh_host_rsa_key')
    transport.add_server_key(host_key)

    server = NoAuthSSHServer()
    transport.start_server(server=server)

    # Additional code to handle SSH sessions
    # Wait for the client to open a session
    channel = transport.accept(20)
    if channel is None:
        print("No channel request.")
        transport.close()
        return

    # Use pty to create a pseudo-terminal for the subprocess
    master_fd, slave_fd = pty.openpty()
    proc = subprocess.Popen('/usr/bin/htop', shell=True, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, close_fds=True)
    os.close(slave_fd)
    reads = [channel, master_fd]

    while True:
        ready_to_read, _, _ = select.select(reads, [], [], 0.1)

        # Exit the loop if the subprocess has ended
        if proc.poll() is not None:
            break

        for fd in ready_to_read:
            # If data is available from the SSH channel, write it to the pseudo-terminal
            if fd == channel:
                data = channel.recv(1024)
                if data:
                    os.write(master_fd, data)
                else:
                    # Close if no data (client disconnected)
                    channel.shutdown(2)
                    proc.terminate()
                    break

            # If data is available from the pseudo-terminal, send it to the SSH channel
            elif fd == master_fd:
                output = os.read(master_fd, 1024)
                if output:
                    channel.send(output)


    # Close the channel and transport after session ends
    channel.close()
    transport.close()

# Set up the server socket
server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind(('::1', 8022))  # Bind to port 22 for SSH
server_socket.listen(100)

print("Paramiko SSH Server running.")

while True:
    client, addr = server_socket.accept()
    print(f"Accepted connection from {addr}")
    client_handler = threading.Thread(target=handle_client, args=(client,))
    client_handler.start()
