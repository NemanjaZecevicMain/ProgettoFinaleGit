from proxmox_client import ProxmoxClient

px = ProxmoxClient()

print("Next ID:", px.get_next_vmid())

newid = px.get_next_vmid()
px.clone_container(102, newid, "test-lxc")

print("Waiting for container unlock...")
px.wait_until_unlocked(newid)

px.set_resources(newid, 1, 512, 6)
px.start_container(newid)

print("Container creato con ID", newid)
