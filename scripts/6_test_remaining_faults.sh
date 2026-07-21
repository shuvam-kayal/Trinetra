#!/bin/bash
FE_IP=$(sudo docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' clab-trinetra-fault-engine)
FE="http://$FE_IP:8000"
echo "Fault engine reachable at: $FE"

fire() {
  local scenario=$1 duration=$2
  curl -s -X POST "$FE/fault/start" \
    -H "Content-Type: application/json" \
    -d "{\"scenario\": \"$scenario\", \"duration_seconds\": $duration}" | python3 -m json.tool
}

echo ""
echo "########## TUNNEL JITTER ##########"
echo "--- Baseline: tc qdisc show dev eth1 on branch-ce1 ---"
sudo docker exec clab-trinetra-branch-ce1 tc qdisc show dev eth1
echo "--- Firing (12s duration) ---"
fire tunnel_jitter 12
echo "--- DURING: should show 'netem delay 15ms 8ms loss 0.5%' under parent 1:30 ---"
sudo docker exec clab-trinetra-branch-ce1 tc qdisc show dev eth1
echo "Waiting 14s for auto-revert..."
sleep 14
echo "--- AFTER: netem qdisc should be gone ---"
sudo docker exec clab-trinetra-branch-ce1 tc qdisc show dev eth1

echo ""
echo "########## ASYMMETRIC DELAY ##########"
echo "--- Baseline: tc qdisc show dev eth2 on core-p1 ---"
sudo docker exec clab-trinetra-core-p1 tc qdisc show dev eth2
echo "--- Firing (12s duration) ---"
fire asymmetric_delay 12
echo "--- DURING: should show 'netem delay 20ms' under parent 1:20 ---"
sudo docker exec clab-trinetra-core-p1 tc qdisc show dev eth2
echo "Waiting 14s for auto-revert..."
sleep 14
echo "--- AFTER: netem qdisc should be gone ---"
sudo docker exec clab-trinetra-core-p1 tc qdisc show dev eth2

echo ""
echo "########## TE PREEMPTION (via fault-engine, not te-engine directly) ##########"
echo "--- Baseline: tc class show dev eth2 on hub-pe1 ---"
sudo docker exec clab-trinetra-hub-pe1 tc class show dev eth2
echo "--- Firing (12s duration) ---"
fire te_preemption 12
echo "--- DURING: class 1:30 ceil should be ~2mbit ---"
sudo docker exec clab-trinetra-hub-pe1 tc class show dev eth2
echo "Waiting 14s for auto-revert..."
sleep 14
echo "--- AFTER: class 1:30 ceil should be back to 100mbit ---"
sudo docker exec clab-trinetra-hub-pe1 tc class show dev eth2

echo ""
echo "########## REKEY STORM ##########"
echo "--- Baseline: tc class + filter show dev eth1 on branch-ce1 ---"
sudo docker exec clab-trinetra-branch-ce1 tc class show dev eth1
sudo docker exec clab-trinetra-branch-ce1 tc filter show dev eth1 parent 1:0
echo "--- Firing (12s duration) ---"
fire rekey_storm 12
echo "--- DURING: new class 1:40 + filters for dport 500/4500 should exist ---"
sudo docker exec clab-trinetra-branch-ce1 tc class show dev eth1
sudo docker exec clab-trinetra-branch-ce1 tc filter show dev eth1 parent 1:0
echo "Waiting 14s for auto-revert..."
sleep 14
echo "--- AFTER: class 1:40 and its filters should be gone ---"
sudo docker exec clab-trinetra-branch-ce1 tc class show dev eth1
sudo docker exec clab-trinetra-branch-ce1 tc filter show dev eth1 parent 1:0

echo ""
echo "########## CONTROLLER POLICY DRIFT ##########"
echo "--- Baseline: tc filter show dev eth1 on branch-ce1 (voice filter should be present) ---"
sudo docker exec clab-trinetra-branch-ce1 tc filter show dev eth1 parent 1:0
echo "--- Firing (12s duration) ---"
fire controller_drift 12
echo "--- DURING: voice (prio 1, tos 0xb8) filter should be GONE - misclassified as bulk ---"
sudo docker exec clab-trinetra-branch-ce1 tc filter show dev eth1 parent 1:0
echo "Waiting 14s for auto-revert..."
sleep 14
echo "--- AFTER: voice filter should be restored ---"
sudo docker exec clab-trinetra-branch-ce1 tc filter show dev eth1 parent 1:0

echo ""
echo "########## Full history check ##########"
curl -s "$FE/fault/history" | python3 -m json.tool