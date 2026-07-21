#!/bin/bash
# Factory 1.9 smoke test - resolves the fault-engine's container IP directly,
# since host port-mapping (localhost:8002) has proven unreliable on this setup.
FE_IP=$(sudo docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' clab-trinetra-fault-engine)
FE="http://$FE_IP:8000"

echo "Fault engine reachable at: $FE"

echo "=== 0. Listing all registered scenarios ==="
curl -s "$FE/fault/scenarios" | python3 -m json.tool

echo ""
echo "=== 1. Baseline tc state on hub-pe1:eth2 ==="
sudo docker exec clab-trinetra-hub-pe1 tc class show dev eth2

echo ""
echo "=== 2. Starting congestion fault (10s duration) ==="
curl -s -X POST "$FE/fault/start" \
  -H "Content-Type: application/json" \
  -d '{"scenario": "congestion", "duration_seconds": 10}' | python3 -m json.tool

echo ""
echo "=== 3. tc state DURING congestion - root ceil should be ~3mbit ==="
sudo docker exec clab-trinetra-hub-pe1 tc class show dev eth2

echo ""
echo "Waiting 12s for auto-revert..."
sleep 12

echo "=== 4. tc state AFTER auto-revert - root ceil should be back to 100mbit ==="
sudo docker exec clab-trinetra-hub-pe1 tc class show dev eth2

echo ""
echo "=== 5. Starting BGP peer drop (15s duration) ==="
curl -s -X POST "$FE/fault/start" \
  -H "Content-Type: application/json" \
  -d '{"scenario": "bgp_drop", "duration_seconds": 15}' | python3 -m json.tool

echo ""
echo "=== 6. BGP state DURING drop ==="
sudo docker exec clab-trinetra-hub-pe1 vtysh -c "show bgp summary"

echo ""
echo "Waiting 17s for auto-revert..."
sleep 17

echo "=== 7. BGP state AFTER auto-revert - should be re-established ==="
sudo docker exec clab-trinetra-hub-pe1 vtysh -c "show bgp summary"

echo ""
echo "=== 8. Full fault history (this IS your topic.fault.events feed) ==="
curl -s "$FE/fault/history" | python3 -m json.tool

echo ""
echo "=== 9. Panic-button test: reset-all ==="
curl -s -X POST "$FE/fault/reset-all" | python3 -m json.tool