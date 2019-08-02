import paramiko
import scp


# %%


class SshManager:
    def __init__(self, _host="192.168.4.3", _user="pi", _passwd="raspberry"):
        self.remote_cwd = "~/"
        self.local_cwd = "~/"
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_client.connect(hostname=_host, username=_user, password=_passwd)
        self.scp_client = scp.SCPClient(self.ssh_client.get_transport())

    def send_cmd(self, cmd):
        stdin, stdout, stderr = self.ssh_client.exec_command(cmd)
        return stdout.read()

    def set_remote_cwd(self, cwd="~/"):
        self.remote_cwd = cwd

    def set_local_cwd(self, cwd="~/"):
        self.local_cwd = cwd

    def transfer_file(self, file, location):
        print("Moving file from '%s' to remote '%s'" % (self.local_cwd + file, self.remote_cwd + location))
        self.scp_client.put(self.local_cwd + file, self.remote_cwd + location)

    def download_file(self, file, location):
        self.scp_client.get(self.remote_cwd + file, self.local_cwd + location)

# %%
