#!/bin/bash
echo "Applying QoS engine to Branch Router..."
# Clear old rules
sudo docker exec clab-trinetra-branch-ce1 tc qdisc del dev eth1 root 2>/dev/null || true

# Build root and default class
sudo docker exec clab-trinetra-branch-ce1 tc qdisc add dev eth1 root handle 1: htb default 30
sudo docker exec clab-trinetra-branch-ce1 tc class add dev eth1 parent 1: classid 1:1 htb rate 100mbit ceil 100mbit

# Build priority classes
sudo docker exec clab-trinetra-branch-ce1 tc class add dev eth1 parent 1:1 classid 1:10 htb rate 20mbit ceil 100mbit prio 1
sudo docker exec clab-trinetra-branch-ce1 tc class add dev eth1 parent 1:1 classid 1:20 htb rate 50mbit ceil 100mbit prio 2
sudo docker exec clab-trinetra-branch-ce1 tc class add dev eth1 parent 1:1 classid 1:30 htb rate 5mbit ceil 100mbit prio 3

# Apply filters
sudo docker exec clab-trinetra-branch-ce1 tc filter add dev eth1 protocol ip parent 1:0 prio 1 u32 match ip tos 0xb8 0xff flowid 1:10
sudo docker exec clab-trinetra-branch-ce1 tc filter add dev eth1 protocol ip parent 1:0 prio 3 u32 match ip tos 0x00 0xff flowid 1:30

echo "QoS successfully applied!"