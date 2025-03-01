import paramiko

import os
import base64
import re
from pathlib import Path

from src.utils_dn42 import load_authorized_keys

# Custom server interface that accepts dn42 maintainers
class SSHServerAuthDn42(paramiko.ServerInterface):
    username = ''

    def check_auth_publickey(self, username, key):
        if not re.match("^[A-Za-z0-9-]+$", username):
            print(f"[AuthDn42] Username {username} contains forbidden characters")
        else:
            authorized_keys = load_authorized_keys(username)
            for authorized_key in authorized_keys:
                if authorized_key == key:
                    print(f"[AuthDn42] Authentication successful for {username} with {key.algorithm_name} key {key.fingerprint}")
                    self.username = username
                    return paramiko.AUTH_SUCCESSFUL
            print(f"[AuthDn42] Authentication failed for {username}")
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return 'publickey'

    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True

    def check_channel_shell_request(self, channel):
        return True

    def get_banner(self):
        motd_path = os.environ['SSH_MOTD_PATH']
        if Path(motd_path).is_file():
            return (Path(motd_path).read_text(), 'en-US')
        else:
            return (None, None)
