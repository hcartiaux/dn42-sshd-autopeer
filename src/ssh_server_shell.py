import paramiko

from src.ssh_server_base      import SSHServerBase
from src.shell import Shell

class SSHServerShell(SSHServerBase):

    def __init__(self, host_key_file, host_key_file_password=None):
        super(SSHServerShell, self).__init__()

        self._host_key = paramiko.RSAKey.from_private_key_file(host_key_file, host_key_file_password)

    def connection_function(self, client, session, channel):
#        try:
            # create the channel and get the stdio
            stdio = channel.makefile('rwU')
            # create the client shell and start it
            # cmdloop() will block execution of this thread.
            self.client_shell = Shell(stdio, stdio)
            self.client_shell.cmdloop()
#        except:
#            pass
