#!/bin/bash

echo "=== 0. Cleaning up Zombie Servers & Forcing IPSec Tunnel UP ==="
sudo docker exec clab-trinetra-dc-1 pkill iperf3
sudo docker exec clab-trinetra-branch-ce1 ipsec up branch-to-hub
sleep 3

echo "=== 1. Starting Receivers ==="
echo "Starting iperf3 servers on Data Center router..."
sudo docker exec -d clab-trinetra-dc-1 iperf3 -s -p 5201   # bulk
sudo docker exec -d clab-trinetra-dc-1 iperf3 -s -p 5203   # bursty/business
sleep 2

echo "=== 2. Launching Congestion (Elephant Flow / Bulk TCP) ==="
echo "Firing 60-second bulk transfer (Capped at 80M to account for IPSec overhead)..."
sudo docker exec -d clab-trinetra-branch-ce1 iperf3 -c 10.0.0.4 -B 10.0.0.3 -p 5201 -t 60 -M 1400 -b 80M --tos 0x00
sleep 2

echo "=== 3. Launching Voice Traffic (Kernel-Tagged ICMP) ==="
echo "Injecting iptables mangle rule to tag Voice ICMP with DSCP 46 (Expedited Forwarding)..."
sudo docker exec clab-trinetra-branch-ce1 iptables -t mangle -A OUTPUT -p icmp -d 10.0.0.4 -j DSCP --set-dscp 46

echo "Firing 10-second VoIP-like call: 160-byte packets every 20ms (G.711-ish)..."
sudo docker exec clab-trinetra-branch-ce1 ping 10.0.0.4 -I 10.0.0.3 -s 160 -i 0.02 -c 500 -q

echo "Cleaning up iptables rule..."
sudo docker exec clab-trinetra-branch-ce1 iptables -t mangle -D OUTPUT -p icmp -d 10.0.0.4 -j DSCP --set-dscp 46

echo "=== 4. Launching Bursty Branch Application Traffic (HTTP-like) ==="
echo "Firing 8 short bursts of small TCP transfers with random gaps, AF21-marked (business traffic)."
for i in $(seq 1 8); do
  sudo docker exec -d clab-trinetra-branch-ce1 iperf3 -c 10.0.0.4 -B 10.0.0.3 -p 5203 -n 200K --tos 0x48
  sleep "0.$((RANDOM % 9 + 1))"
done
sleep 3

echo "=== 5. Validating QoS Queues ==="
echo "Notice how Class 1:30 (Bulk) has massive overlimits, while 1:10 (Voice) is active and clean:"
sudo docker exec clab-trinetra-branch-ce1 tc -s class show dev eth1

echo ""
echo "=== 6. Validating Telemetry Sensor ==="
echo "Proving softflowd captured the packets for Person B's pipeline:"
sudo docker exec clab-trinetra-branch-ce1 softflowctl -c /tmp/softflowd-eth1.ctl statistics