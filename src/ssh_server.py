import paramiko
import os
import pty
import subprocess
import select

from src.ssh_server_base      import SSHServerBase
from src.ssh_server_auth_none import SSHServerAuthNone

class SSHServer(SSHServerBase):

    def __init__(self, host_key_file, host_key_file_password=None):
        super(SSHServer, self).__init__()

        self._host_key = paramiko.RSAKey.from_private_key_file(host_key_file, host_key_file_password)

    def connection_function(self, client):
        try:
            # create the SSH transport object
            session = paramiko.Transport(client)
            session.add_server_key(self._host_key)

            # start the SSH server
            try:
                session.start_server(server=self._server)
            except paramiko.SSHException:
                return
            channel = session.accept()
            if channel is None:
                print("No channel request.")
                session.close()
                return

            # Use pty to create a pseudo-terminal for the subprocess
            master_fd, slave_fd = pty.openpty()
            proc = subprocess.Popen('/usr/bin/htop', shell=True, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd, close_fds=True)
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
                        output = os.read(master_fd, 1024)
                        if output:
                            channel.send(output)


            # Close the channel and transport after session ends
            channel.close()
            session.close()

        except:
            pass
