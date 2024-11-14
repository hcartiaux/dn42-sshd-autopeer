import os
from src.ssh_server_shell import SSHServerShell
# from src.ssh_server_pipe import SSHServerPipe
from src.ssh_server_auth_none import SSHServerAuthNone

if __name__ == '__main__':
    cmd = 'htop'
    host_key_file = os.path.dirname(os.path.realpath(__file__)) + "/ssh-keys/ssh_host_rsa_key"

    server = SSHServerShell(host_key_file)
    # server = SSHServerPipe(cmd, host_key_file)

    server.set_server_interface(SSHServerAuthNone())

    # Start the server, you can give it a custom IP address and port, or
    # leave it empty to run on 127.0.0.1:22
    server.start("::1", int(os.getenv("SSH_PORT", 8022)))
