import paramiko

import os
import pty
import subprocess
import select

from src.ssh_server_base      import SSHServerBase

class SSHServerPipe(SSHServerBase):

    def __init__(self, cmd, host_key_file, host_key_file_password=None):
        super(SSHServerPipe, self).__init__()
        self._cmd = cmd
        self._host_key = paramiko.RSAKey.from_private_key_file(host_key_file, host_key_file_password)

    def connection_function(self, client, session, channel):
        try:

            # Use pty to create a pseudo-terminal for the subprocess
            master_fd, slave_fd = pty.openpty()
            proc = subprocess.Popen(self._cmd, shell=True, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, close_fds=True)
            os.close(slave_fd)

            reads = [channel, master_fd]
            while True:
                ready_to_read, _, _ = select.select(reads, [], [], 0.1)

                # Exit the loop if the subprocess has ended
                if proc.poll() is not None:
                    break

                for fd in ready_to_read:
                    # If data is available from the SSH channel, write it to the pseudo-terminal
                    if fd == channel:
                        data = channel.recv(1024)
                        if data:
                            os.write(master_fd, data)
                        else:
                            # Close if no data (client disconnected)
                            channel.shutdown(2)
                            proc.terminate()
                            break

                    # If data is available from the pseudo-terminal, send it to the SSH channel
                    elif fd == master_fd:
                        data = os.read(master_fd, 1024)
                        if data:
                            channel.send(data)

        except:
            pass
