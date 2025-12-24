import os
import time
import subprocess
import requests


class ProxmoxClient:
    """
    Client di integrazione con Proxmox VE.
    Combina:
    - API REST (clone, config, start)
    - SSH verso il nodo (password, IP container)
    """

    def __init__(self):
        # Base URL API Proxmox (es: https://host:8006/api2/json)
        self.base = (os.getenv("PROXMOX_HOST") or "").rstrip("/")
        self.node = os.getenv("PROXMOX_NODE")
        self.storage = os.getenv("PROXMOX_STORAGE", "local-lvm")

        # Credenziali API (token)
        user = os.getenv("PROXMOX_USER")
        token_name = os.getenv("PROXMOX_TOKEN_NAME")
        token_value = os.getenv("PROXMOX_TOKEN_VALUE")

        # Parametri SSH verso il nodo Proxmox
        self.ssh_host = os.getenv("PROXMOX_SSH_HOST")
        self.ssh_user = os.getenv("PROXMOX_SSH_USER", "root")
        self.ssh_key = os.getenv("PROXMOX_SSH_KEY")

        # Verifica variabili API
        if not all([self.base, self.node, user, token_name, token_value]):
            raise Exception("Variabili Proxmox mancanti")

        # Verifica variabili SSH
        if not all([self.ssh_host, self.ssh_user, self.ssh_key]):
            raise Exception("Variabili SSH mancanti")

        # Sessione HTTP persistente con header di autenticazione
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"PVEAPIToken={user}!{token_name}={token_value}"
        })

    def _url(self, path):
        """Costruisce l’URL completo per le API Proxmox"""
        return f"{self.base}{path}"

    # -------------------------
    # NETWORK
    # -------------------------
    def get_container_ip(self, vmid):
        """
        Recupera l’indirizzo IP IPv4 del container
        eseguendo un comando all’interno del CT via pct exec.
        """
        cmd = [
            "ssh",
            "-i", self.ssh_key,
            "-o", "StrictHostKeyChecking=no",
            f"{self.ssh_user}@{self.ssh_host}",
            f"pct exec {vmid} -- ip -4 addr show eth0"
        ]

        p = subprocess.run(cmd, capture_output=True, text=True)

        if p.returncode != 0:
            raise Exception(p.stderr.strip())

        # Parsing output comando ip
        for line in p.stdout.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                return line.split()[1].split("/")[0]

        raise Exception("IP non trovato nel container")

    # -------------------------
    # TASK API
    # -------------------------
    def _wait_task(self, upid, timeout=600):
        """
        Attende il completamento di un task Proxmox (UPID).
        Necessario perché le API sono asincrone.
        """
        start = time.time()
        while True:
            r = self.session.get(
                self._url(f"/nodes/{self.node}/tasks/{upid}/status"),
                verify=False
            )
            r.raise_for_status()
            data = r.json()["data"]

            if data["status"] == "stopped":
                if data.get("exitstatus") not in (None, "OK"):
                    raise Exception(data.get("exitstatus"))
                return

            if time.time() - start > timeout:
                raise Exception("Timeout Proxmox")

            time.sleep(2)

    def get_next_vmid(self):
        """Ottiene il prossimo VMID libero dal cluster Proxmox"""
        r = self.session.get(self._url("/cluster/nextid"), verify=False)
        r.raise_for_status()
        return int(r.json()["data"])

    # -------------------------
    # LXC MANAGEMENT
    # -------------------------
    def clone_container(self, template_id, new_id, hostname):
        """
        Clona un template LXC esistente in un nuovo container.
        """
        r = self.session.post(
            self._url(f"/nodes/{self.node}/lxc/{template_id}/clone"),
            data={
                "newid": new_id,
                "hostname": hostname,
                "storage": self.storage,
                "full": 1
            },
            verify=False
        )
        r.raise_for_status()
        self._wait_task(r.json()["data"])
        time.sleep(20)

    def configure_and_start(self, vmid, cores, memory, disk):
        """
        Configura risorse hardware del container
        e ne avvia l’esecuzione.
        """
        self.session.put(
            self._url(f"/nodes/{self.node}/lxc/{vmid}/config"),
            data={"cores": cores, "memory": memory},
            verify=False
        ).raise_for_status()

        time.sleep(15)

        self.session.put(
            self._url(f"/nodes/{self.node}/lxc/{vmid}/resize"),
            data={"disk": "rootfs", "size": f"{disk}G"},
            verify=False
        ).raise_for_status()

        time.sleep(20)

        r = self.session.post(
            self._url(f"/nodes/{self.node}/lxc/{vmid}/status/start"),
            verify=False
        )
        r.raise_for_status()
        self._wait_task(r.json()["data"], 180)

        time.sleep(20)

    # -------------------------
    # PASSWORD
    # -------------------------
    def set_root_password(self, vmid, password):
        """
        Imposta la password di root nel container
        usando expect per automatizzare passwd.
        """
        expect_script = f"""
spawn pct exec {vmid} -- passwd root
expect "New password:"
send "{password}\\r"
expect "Retype new password:"
send "{password}\\r"
expect eof
"""

        cmd = [
            "ssh",
            "-i", self.ssh_key,
            "-o", "StrictHostKeyChecking=no",
            f"{self.ssh_user}@{self.ssh_host}",
            "expect"
        ]

        p = subprocess.run(
            cmd,
            input=expect_script,
            text=True,
            capture_output=True
        )

        if p.returncode != 0:
            raise Exception(p.stderr.strip())
