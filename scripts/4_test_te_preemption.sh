#!/bin/bash
TE_IP=$(sudo docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' clab-trinetra-te-engine)
TE="http://$TE_IP:8000"

echo "=== 1. Baseline LSP state ==="
curl -s "$TE/lsps" | python3 -m json.tool

echo ""
echo "=== 2. Baseline tc state on hub-pe1:eth2 (bulk class 1:30) ==="
sudo docker exec clab-trinetra-hub-pe1 tc class show dev eth2

echo ""
echo "=== 3. Triggering TE preemption fault ==="
curl -s -X POST "$TE/fault/te-preempt" | python3 -m json.tool

echo ""
echo "=== 4. tc state AFTER preemption - bulk ceil should now be ~2mbit ==="
sudo docker exec clab-trinetra-hub-pe1 tc class show dev eth2

echo ""
echo "=== 5. Telemetry snapshot (matches topic.tunnel.health te_metrics shape) ==="
curl -s "$TE/telemetry/te" | python3 -m json.tool

echo ""
echo "=== 6. Restoring secondary LSP ==="
curl -s -X POST "$TE/fault/te-restore" | python3 -m json.tool

echo ""
echo "=== 7. tc state AFTER restore - bulk ceil should be back to 100mbit ==="
sudo docker exec clab-trinetra-hub-pe1 tc class show dev eth2
