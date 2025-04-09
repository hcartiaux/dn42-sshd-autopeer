import logging
import os
import paramiko
import re
from pathlib import Path
from src.utils_dn42 import load_authorized_keys
from packaging.version import Version


class SSHServerAuthDn42(paramiko.ServerInterface):
    """
    Custom SSH server authentication interface for DN42 network maintainers.

    Implements Paramiko's ServerInterface to provide custom authentication
    using public key verification based on Dn42 registry.

    Attributes:
        last_login (str): Stores the authenticated username of the last successful login.
    """

    last_login = ''

    def check_auth_publickey(self, username, key):
        """
        Authenticate a user using their public key.

        Validates the username format and checks against registered ssh public
        keys in the maintainer objects of the Dn42 registry.

        Parameters:
            username (str): The username attempting to authenticate.
            key (paramiko.PKey): The public key used for authentication.

        Returns:
            int: Authentication result (paramiko.AUTH_SUCCESSFUL or paramiko.AUTH_FAILED)
        """
        if not re.match("^[A-Za-z0-9-]+$", username):
            logging.warning(f"[AuthDn42] Username {username} contains forbidden characters")
        else:
            authorized_keys = load_authorized_keys(username)
            for authorized_key in authorized_keys:
                if authorized_key == key:
                    log_str = f"[AuthDn42] Authentication successful for {username}"
                    if Version(paramiko.__version__) >= Version('3.2'):
                        log_str += f" with {key.algorithm_name} key {key.fingerprint}"
                    logging.info(log_str)
                    self.last_login = username
                    return paramiko.AUTH_SUCCESSFUL
            logging.warning(f"[AuthDn42] Authentication failed for {username}")
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        """
        Specify the authentication methods allowed for the server.

        Parameters:
            username (str): The username attempting to authenticate.

        Returns:
            str: Always returns 'publickey' to allow public key authentication only.
        """
        return 'publickey'

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
