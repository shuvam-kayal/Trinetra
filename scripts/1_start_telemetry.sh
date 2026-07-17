#!/bin/bash
# Factory 1.6 - IPFIX export, now on every physical interface of every router
# node (was branch-ce1:eth1 only). softflowd monitors one interface per
# instance, so multi-homed nodes (core-p1, hub-pe1) get one instance per link.
COLLECTOR="10.0.0.99:2055"   # TODO: confirm real pmacct collector IP with Person B

declare -A NODE_IFACES=(
  ["clab-trinetra-branch-ce1"]="eth1"
  ["clab-trinetra-hub-pe1"]="eth1 eth2"
  ["clab-trinetra-core-p1"]="eth1 eth2"
  ["clab-trinetra-dc-1"]="eth1"
)

for node in "${!NODE_IFACES[@]}"; do
  for iface in ${NODE_IFACES[$node]}; do
    echo "Starting softflowd on $node ($iface)..."
    sudo docker exec -d "$node" softflowd -i "$iface" -n "$COLLECTOR" -v 10 \
      -c "/tmp/softflowd-${iface}.ctl" -p "/tmp/softflowd-${iface}.pid"
  done
done

echo "Telemetry sensors are active on all interfaces, all 4 nodes!"
