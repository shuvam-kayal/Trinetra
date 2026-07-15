#!/bin/bash

echo "=== 1. Starting Receivers ==="
echo "Starting iperf3 servers on Data Center router..."
sudo docker exec -d clab-trinetra-dc-1 iperf3 -s -p 5201
sudo docker exec -d clab-trinetra-dc-1 iperf3 -s -p 5202
sleep 2

echo "=== 2. Launching Congestion ==="
echo "Firing 60-second Elephant Flow (Bulk Traffic) in the background..."
sudo docker exec -d clab-trinetra-branch-ce1 iperf3 -c 10.0.0.4 -B 10.0.0.3 -p 5201 -t 60 -M 1400 --tos 0x00
sleep 2

echo "=== 3. Launching Premium Traffic ==="
echo "Firing 10-second VoIP Call (Premium Traffic) in the foreground."
echo "Watch this get priority bandwidth:"
sudo docker exec clab-trinetra-branch-ce1 iperf3 -c 10.0.0.4 -B 10.0.0.3 -p 5202 -t 10 -M 1400 --tos 0xb8

echo ""
echo "=== 4. Validating QoS Queues ==="
echo "Notice how Class 1:30 (Bulk) has massive overlimits, while 1:10 (Premium) is clean:"
sudo docker exec clab-trinetra-branch-ce1 tc -s class show dev eth1

echo ""
echo "=== 5. Validating Telemetry Sensor ==="
echo "Proving softflowd captured the packets for Person B's pipeline:"
sudo docker exec clab-trinetra-branch-ce1 softflowctl -c /tmp/softflowd.ctl statistics