# Trinetra SD-WAN Simulation Network

## Prerequisites
- Ubuntu WSL2 with Native Docker installed.
- ContainerLab installed.

## How to Start the Network
1. Build the images by movinf into respective directories: `cd ~/trinetra-sim/sdwan-controller`
                                                           `sudo docker build -t trinetra-controller:v1 .`
                                                           `cd ~/trinetra-sim/te-engine`
                                                           `sudo docker build -t trinetra-te-engine:v1 .`
2. Deploy the topology: `sudo clab deploy -t trinetra.yaml`
3. Start the IPSec Tunnels:
   - `sudo docker exec clab-trinetra-branch-ce1 ipsec start`
   - `sudo docker exec clab-trinetra-hub-pe1 ipsec start`
4. Start the Scripts
   - `sudo bash scripts/1_start_telemetry.sh`
   - `sudo bash scripts/2_apply_qos.sh`
   - `sudo bash scripts/3_generate_traffic.sh`
   - `sudo bash scripts/4_test_te_preemption.sh`


## Useful Troubleshooting Commands

**Check Core Router Telemetry (Interface Specific):**
`sudo docker exec clab-trinetra-core-p1 softflowctl -c /tmp/softflowd-eth1.ctl statistics`

**Verify Data Center Routing Table:**
`sudo docker exec clab-trinetra-dc-1 vtysh -c "show ip route"`

**Get te-engine's IP**
`sudo docker exec clab-trinetra-te-engine hostname -i`

**Check Controller API State:**
`curl http://<CONTROLLER_IP>:8000/telemetry/state`
`curl http://<TE-Engine IP>:8000/lsps`

**Showcase Factory 1.2 (BGP Underlay):**
`sudo docker exec clab-trinetra-hub-pe1 vtysh -c "show bgp summary"`

**Showcase Factory 1.3 (IPSec Overlay):**
`sudo docker exec clab-trinetra-branch-ce1 ipsec status`

**Showcase Factory 1.7 (QoS Engine):**
`sudo docker exec clab-trinetra-branch-ce1 tc -s class show dev eth1`