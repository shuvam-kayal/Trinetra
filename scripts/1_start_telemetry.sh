#!/bin/bash
echo "Starting softflowd on Branch Router..."
sudo docker exec -d clab-trinetra-branch-ce1 softflowd -i eth1 -n 10.0.0.99:2055 -v 10 -c /tmp/softflowd.ctl -p /tmp/softflowd.pid
echo "Telemetry sensors are active!"