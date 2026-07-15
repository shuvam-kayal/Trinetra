# Start with the official FRRouting image
FROM frrouting/frr:latest

# Install strongSwan (VPN), softflowd (Telemetry), iperf3 (Traffic), and iproute2 (QoS)
RUN apk update && apk add --no-cache strongswan softflowd iperf3 iproute2