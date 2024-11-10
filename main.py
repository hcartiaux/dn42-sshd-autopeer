import os
from src.ssh_server import SSHServer

if __name__ == '__main__':
    server = SSHServer(os.path.dirname(os.path.realpath(__file__)) + "/ssh-keys/ssh_host_rsa_key")

    # Start the server, you can give it a custom IP address and port, or
    # leave it empty to run on 127.0.0.1:22
    server.start("::1", int(os.getenv("SSH_PORT", 8022)))
