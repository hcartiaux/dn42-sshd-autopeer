import os
import sys
import argparse

def main():
    top_directory = os.path.dirname(os.path.realpath(__file__))
    host_key_file = top_directory + '/' + '/files/ssh-keys/ssh_host_rsa_key'

    # Configuration as environment variables
    os.environ['DN42_SSH_LISTEN_ADDRESS'] = os.getenv('DN42_SSH_LISTEN_ADDRESS', '::1')
    os.environ['DN42_SSH_PORT'] = os.getenv('DN42_SSH_PORT', '8022')
    os.environ['DN42_SERVER'] = os.getenv('DN42_SERVER', 'nl-ams2.flap42.eu')
    os.environ['DN42_DB_PATH'] = os.getenv('DN42_DB_PATH', top_directory + '/' + 'files/db/' + os.environ['DN42_SERVER'])
    os.environ['DN42_REGISTRY_DIRECTORY'] = os.getenv(
        'DN42_REGISTRY_DIRECTORY', top_directory + '/' + 'files/registry')
    os.environ['DN42_ASN'] = os.getenv('DN42_ASN', '4242420263')
    os.environ['DN42_WG_PUB_KEY'] = os.getenv('DN42_WG_PUB_KEY', 'rj0SORruOE/hGVJ5IkDXNedsL9Nxs8j0kTujRB01XXk=')
    os.environ['DN42_WG_LINK_LOCAL'] = os.getenv('DN42_WG_LINK_LOCAL', 'fe80:0263::')
    os.environ['DN42_WG_BASE_PORT'] = os.getenv('DN42_WG_BASE_PORT', '52000')

    # Command line parameters
    parser = argparse.ArgumentParser(prog='dn42-sshd')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--gaming',
        help='Start the gaming server',
        action='store_true')
    group.add_argument(
        '--peering',
        help='Start the auto peering server',
        action='store_true')
    try:
        args = parser.parse_args()
    except BaseException:
        sys.exit(1)

    if args.peering:
        # Create a SSH server, authenticating on the Dn42 registry, serving ShellDn42
        from src.shell_dn42 import ShellDn42
        from src.ssh_server_shell import SSHServerShell
        from src.ssh_server_auth_dn42 import SSHServerAuthDn42
        from src.utils_dn42 import database

        os.environ['DN42_SSH_MOTD_PATH'] = os.getenv(
            'DN42_SSH_MOTD_PATH', top_directory + '/' + 'files/motd/' + os.environ['DN42_SERVER'])

        # Create the database if necessary
        database()

        server = SSHServerShell(ShellDn42, host_key_file)
        server.set_server_interface(SSHServerAuthDn42())
    elif args.gaming:
        # Create a SSH server, without authentication, serving the command advent
        from src.ssh_server_pipe import SSHServerPipe
        from src.ssh_server_auth_none import SSHServerAuthNone

        os.environ['DN42_SSH_MOTD_PATH'] = os.getenv(
            'DN42_SSH_MOTD_PATH', top_directory + '/' + 'files/motd/motd_gaming_service')
        cmd = 'advent'
        server = SSHServerPipe(cmd, host_key_file)
        server.set_server_interface(SSHServerAuthNone())

    # Start the server, you can give it a custom listen IP address and port, or
    # leave it empty to run on 127.0.0.1:22
    server.start(os.environ['DN42_SSH_LISTEN_ADDRESS'], int(os.environ['DN42_SSH_PORT']))

if __name__ == '__main__':
    main()
