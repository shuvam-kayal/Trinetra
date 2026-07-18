#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e 

echo "=== 1. Compiling Docker Images ==="
echo "Building Core Router Image..."
sudo docker build -t trinetra-router:v1 .

echo "Building Traffic Engineering (TE) Engine Image..."
cd te-engine
sudo docker build -t trinetra-te-engine:v1 .
cd ..

echo "Building SD-WAN Controller Image..."
cd sdwan-controller
sudo docker build -t trinetra-controller:v1 .
cd ..

echo ""
echo "=== 2. Resetting and Deploying Data Plane (ContainerLab) ==="
sudo clab destroy -t trinetra.yaml
sudo clab deploy -t trinetra.yaml

echo ""
echo "=== 3. Booting IPSec Cryptography Daemons ==="
sudo docker exec clab-trinetra-branch-ce1 ipsec start
sudo docker exec clab-trinetra-hub-pe1 ipsec start
echo "Waiting 3 seconds for IKE/ESP daemons to initialize..."
sleep 3

echo ""
echo "=== 4. Initializing Telemetry Sensors (Factory 1.8) ==="
sudo bash scripts/1_start_telemetry.sh

echo ""
echo "=== 5. Injecting QoS Queues (Factory 1.7) ==="
sudo bash scripts/2_apply_qos.sh

echo ""
echo "========================================================"
echo "    NETWORK INITIALIZATION AND BASELINE COMPLETE        "
echo "========================================================"
echo "The simulation is completely fresh, sensors are active,"
echo "and queues are built. You can now safely execute other commands."