import os

from src.shell_dn42 import ShellDn42
from src.ssh_server_shell import SSHServerShell
from src.ssh_server_auth_dn42 import SSHServerAuthDn42

# from src.ssh_server_pipe import SSHServerPipe
# from src.ssh_server_auth_none import SSHServerAuthNone


if __name__ == '__main__':

    os.environ['SSH_PORT']                = os.getenv('SSH_PORT', '8022')
    os.environ['SSH_MOTD_PATH']           = os.getenv('SSH_MOTD_PATH', 'files/motd')
    os.environ['DN42_REGISTRY_DIRECTORY'] = os.getenv('DN42_REGISTRY_DIRECTORY', 'files/registry')

    host_key_file = os.path.dirname(os.path.realpath(__file__)) + "files/ssh-keys/ssh_host_rsa_key"

    server = SSHServerShell(ShellDn42, host_key_file)
    server.set_server_interface(SSHServerAuthDn42())

    # cmd = 'htop'
    # server = SSHServerPipe(cmd, host_key_file)
    # server.set_server_interface(SSHServerAuthNone())

    # Start the server, you can give it a custom IP address and port, or
    # leave it empty to run on 127.0.0.1:22
    server.start("::1", int(os.getenv("SSH_PORT", 8022)))
