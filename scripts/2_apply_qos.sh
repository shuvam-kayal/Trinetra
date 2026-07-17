#!/bin/bash
# Factory 1.7 - QoS engine, now on every physical interface of every router
# node (was branch-ce1:eth1 only). Classes match sdwan-controller/main.py
# exactly - keep both in sync if you change this.

declare -A NODE_IFACES=(
  ["clab-trinetra-branch-ce1"]="eth1"
  ["clab-trinetra-hub-pe1"]="eth1 eth2"
  ["clab-trinetra-core-p1"]="eth1 eth2"
  ["clab-trinetra-dc-1"]="eth1"
)

apply_qos() {
  local node=$1 iface=$2
  echo "Applying QoS to $node ($iface)..."
  sudo docker exec "$node" tc qdisc del dev "$iface" root 2>/dev/null || true
  sudo docker exec "$node" tc qdisc add dev "$iface" root handle 1: htb default 30
  sudo docker exec "$node" tc class add dev "$iface" parent 1: classid 1:1 htb rate 100mbit ceil 100mbit
  sudo docker exec "$node" tc class add dev "$iface" parent 1:1 classid 1:10 htb rate 20mbit ceil 100mbit prio 1
  sudo docker exec "$node" tc class add dev "$iface" parent 1:1 classid 1:20 htb rate 50mbit ceil 100mbit prio 2
  sudo docker exec "$node" tc class add dev "$iface" parent 1:1 classid 1:30 htb rate 5mbit  ceil 100mbit prio 3
  sudo docker exec "$node" tc filter add dev "$iface" protocol ip parent 1:0 prio 1 u32 match ip tos 0xb8 0xff flowid 1:10
  sudo docker exec "$node" tc filter add dev "$iface" protocol ip parent 1:0 prio 2 u32 match ip tos 0x48 0xff flowid 1:20
  sudo docker exec "$node" tc filter add dev "$iface" protocol ip parent 1:0 prio 3 u32 match ip tos 0x00 0xff flowid 1:30
}

for node in "${!NODE_IFACES[@]}"; do
  for iface in ${NODE_IFACES[$node]}; do
    apply_qos "$node" "$iface"
  done
done

echo "QoS successfully applied to all nodes!"
