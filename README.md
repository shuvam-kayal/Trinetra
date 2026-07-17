# Trinetra SD-WAN Simulation Network

## Prerequisites
- Ubuntu WSL2 with Native Docker installed.
- ContainerLab installed.

## How to Start the Network
1. Build the custom router image: `sudo docker build -t trinetra-router:v1 .`
2. Deploy the topology: `sudo clab deploy -t trinetra.yaml`
3. Start the IPSec Tunnels:
   - `sudo docker exec clab-trinetra-branch-ce1 ipsec start`
   - `sudo docker exec clab-trinetra-hub-pe1 ipsec start`


## Useful Troubleshooting Commands

**Check Core Router Telemetry (Interface Specific):**
`sudo docker exec clab-trinetra-core-p1 softflowctl -c /tmp/softflowd-eth1.ctl statistics`

**Verify Data Center Routing Table:**
`sudo docker exec clab-trinetra-dc-1 vtysh -c "show ip route"`

**Check Controller API State:**
`curl http://<CONTROLLER_IP>:8000/telemetry/state`