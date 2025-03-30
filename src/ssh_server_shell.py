import logging
import os
import paramiko
from src.ssh_server_base import SSHServerBase


class SSHServerShell(SSHServerBase):
    """
    Specialized SSH server that manages an interactive shell session.

    Extends the SSHServerBase to create and manage a custom shell
    for each incoming SSH connection, using a provided shell class.

    Attributes:
        shell_class (type): The class used to instantiate the interactive shell.
        _host_key (paramiko.RSAKey): SSH host key for server authentication.
    """

    def __init__(self, shell_class, host_key_file, host_key_file_password=None):
        """
        Initialize the SSH server shell with a specific shell class and host key.

        Parameters:
            shell_class (type): The class to be used for creating interactive shells.
            host_key_file (str): Path to the SSH host key private key file.
            host_key_file_password (str, optional): Password for the host key file.
                                                    Defaults to None.
        """
        super(SSHServerShell, self).__init__()
        self.shell_class = shell_class
        self._host_key = paramiko.RSAKey.from_private_key_file(host_key_file, host_key_file_password)

    def connection_function(self, client, session, channel, username):
        """
        Handle individual SSH connection by creating and running a shell instance.

        Manages the lifecycle of a shell for each incoming SSH connection:
        - Creates file-like stdio objects from the SSH channel
        - Instantiates a shell with connection-specific parameters
        - Runs the shell's command loop
        - Ensures proper cleanup of channel and session

        Parameters:
            client (socket.socket): The connected client socket.
            session (paramiko.Transport): The SSH transport session.
            channel (paramiko.Channel): The SSH communication channel.
            username (str): The SSH username.

        Notes:
            - Uses environment variables DN42_ASN and DN42_SERVER for shell configuration
            - Logs any exceptions during shell execution
            - Closes channel and session after shell completes or fails
        """
        try:
            # create the channel and get the stdio
            stdio = channel.makefile('rwU')
            # create the client shell
            self.client_shell = self.shell_class(
                username,
                stdio,
                stdio,
                asn=os.environ['DN42_ASN'],
                server=os.environ['DN42_SERVER'])
            # start the shell
            # cmdloop() will block execution of this thread.
            self.client_shell.cmdloop()
        except BaseException:
            logging.exception(f"[{threading.get_ident()}][SSHServerShell] Execution error in the shell of {username}")

        # Close the channel and transport after session ends
        channel.close()
        session.close()
