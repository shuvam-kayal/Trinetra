# Start with the official FRRouting image (which is based on Alpine Linux)
FROM frrouting/frr:latest

# Install strongSwan using the Alpine package manager
RUN apk update && apk add --no-cache strongswan
