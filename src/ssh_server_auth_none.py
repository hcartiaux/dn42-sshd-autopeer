import os
import paramiko
from pathlib import Path


class SSHServerAuthNone(paramiko.ServerInterface):
    """
    Custom SSH server authentication interface that accepts all authentication attempts.

    Provides a permissive authentication mechanism that automatically
    allows any authentication attempt without detailed verification.

    Attributes:
        last_login (str): Stores the last accepted username
    """

    last_login = ''

    def check_auth_none(self, username):
        """
        Automatically approve authentication attempts without validation.

        Parameters:
            username (str): The username attempting to authenticate.

        Returns:
            int: Always returns AUTH_SUCCESSFUL, allowing any username.
        """
        self.last_login = username
        return paramiko.AUTH_SUCCESSFUL

    def check_channel_request(self, kind, chanid):
        """
        Validate incoming channel open requests.

        Parameters:
            kind (str): The type of channel being requested.
            chanid (int): The channel ID.

        Returns:
            int: Channel open status (paramiko.OPEN_SUCCEEDED or
                 paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED)
        """
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        """
        Handle pseudo-terminal (PTY) requests from the client.

        Parameters:
            channel (paramiko.Channel): The SSH channel.
            term (str): Terminal type.
            width (int): Terminal width in characters.
            height (int): Terminal height in characters.
            pixelwidth (int): Terminal width in pixels.
            pixelheight (int): Terminal height in pixels.
            modes (dict): Terminal modes.

        Returns:
            bool: Always returns True to accept PTY requests.
        """
        return True

    def check_channel_shell_request(self, channel):
        """
        Handle shell requests from the client.

        Parameters:
            channel (paramiko.Channel): The SSH channel.

        Returns:
            bool: Always returns True to accept shell requests.
        """
        return True

    def get_banner(self):
        """
        Retrieve the message of the day (MOTD) for the SSH connection.

        Reads the MOTD from a file specified in the DN42_SSH_MOTD_PATH
        environment variable.

        Returns:
            tuple: A tuple containing (banner_text, language), or (None, None)
                   if the MOTD file is not found.
        """
        motd_path = os.environ['DN42_SSH_MOTD_PATH']
        if Path(motd_path).is_file():
            return (Path(motd_path).read_text(), 'en-US')
        else:
            return (None, None)
