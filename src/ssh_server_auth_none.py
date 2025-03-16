import paramiko
import os
from pathlib import Path

# Custom server interface that accepts any authentication attempt


class SSHServerAuthNone(paramiko.ServerInterface):
    def check_auth_none(self, username):
        return paramiko.AUTH_SUCCESSFUL

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
