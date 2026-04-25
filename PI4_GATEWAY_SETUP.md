# Raspberry Pi 4 Gateway Setup Guide

This guide explains how to set up the Gateway service on a Raspberry Pi 4 for the University Attendance system.

Target outcome:
- Gateway starts on boot
- Gateway connects to MQTT broker
- Gateway forwards attendance to backend
- Gateway performs template sync and heartbeat

## 1. What You Are Setting Up

The Gateway service is the bridge between device traffic and backend APIs.

Data flow:
1. ESP32 devices publish encrypted attendance scans to MQTT
2. Gateway consumes scans and queues them
3. Gateway forwards records to backend API
4. Gateway polls pending template sync tasks
5. Gateway sends heartbeat and publishes health

## 2. Prerequisites

Hardware:
- Raspberry Pi 4 (4 GB RAM or higher recommended)
- Stable network connection

Software:
- Raspberry Pi OS 64-bit (Bookworm recommended)
- Python 3.11 or compatible
- Mosquitto broker (local or remote)
- Backend API reachable from Pi

You must know these values:
- Backend URL
- Device service token
- AES key
- MQTT broker host and port

## 3. Prepare the Pi

Run:

    sudo apt update && sudo apt upgrade -y
    sudo apt install -y git python3 python3-venv python3-pip mosquitto mosquitto-clients

Optional but recommended if you want Redis-based dedup on Pi:

    sudo apt install -y redis-server

## 4. Get the Project

Run:

    mkdir -p ~/projects
    cd ~/projects
    git clone <YOUR_REPOSITORY_URL> UNI-ATTENDENSE-WITH-IoT.v.10
    cd UNI-ATTENDENSE-WITH-IoT.v.10/gateway

## 5. Create Python Environment

Run:

    python3 -m venv .venv
    source .venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

## 6. Create Gateway Environment File

Create file:

    nano .env.gateway

Paste and edit values:

    MQTT_BROKER=127.0.0.1
    MQTT_PORT=1883

    REDIS_HOST=127.0.0.1
    REDIS_PORT=6379

    BACKEND_URL=http://<BACKEND_HOST_OR_IP>:8000
    DEVICE_SERVICE_TOKEN=<YOUR_DEVICE_SERVICE_TOKEN>
    AES_KEY=<YOUR_AES_KEY>

    SYNC_POLL_INTERVAL=30

Notes:
- If Redis is not running, gateway still starts but dedup becomes limited.
- Keep DEVICE_SERVICE_TOKEN and AES_KEY identical to backend/device configuration.

## 7. Important Integration Fix Before Running

Current project behavior mismatch:
- Backend device-facing endpoints validate x-device-token header.
- Gateway currently sends Authorization Bearer for those endpoints.

If not fixed, gateway calls can fail with 401.

Update gateway headers in the following call paths to send:

    x-device-token: <DEVICE_SERVICE_TOKEN>

Endpoints affected:
- POST /api/attendance
- GET /api/templates/pending-sync
- POST /api/templates/sync-ack
- POST /api/gateway/heartbeat

## 8. Start and Test Gateway Manually

From gateway directory:

    source .venv/bin/activate
    set -a && source .env.gateway && set +a
    python -u gateway_service.py

Expected logs include:
- MQTT broker available
- Backend API available
- Redis connected (or warning if unavailable)
- 4 worker threads started

## 9. Validate MQTT and Heartbeat

In a second terminal on Pi:

    mosquitto_sub -h 127.0.0.1 -t gateway/health -v

You should see periodic JSON health messages.

Validate backend health endpoint from Pi:

    curl http://<BACKEND_HOST_OR_IP>:8000/api/health

## 10. Run Gateway as a Service (Auto-start)

Create systemd service:

    sudo nano /etc/systemd/system/attendance-gateway.service

Use this content:

    [Unit]
    Description=Attendance Gateway Service
    After=network-online.target mosquitto.service
    Wants=network-online.target

    [Service]
    Type=simple
    User=pi
    WorkingDirectory=/home/pi/projects/UNI-ATTENDENSE-WITH-IoT.v.10/gateway
    EnvironmentFile=/home/pi/projects/UNI-ATTENDENSE-WITH-IoT.v.10/gateway/.env.gateway
    ExecStart=/home/pi/projects/UNI-ATTENDENSE-WITH-IoT.v.10/gateway/.venv/bin/python -u gateway_service.py
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target

Enable and start:

    sudo systemctl daemon-reload
    sudo systemctl enable attendance-gateway
    sudo systemctl start attendance-gateway

Check status and logs:

    sudo systemctl status attendance-gateway
    sudo journalctl -u attendance-gateway -f

## 11. Common Troubleshooting

A. Backend unreachable
- Check BACKEND_URL in .env.gateway
- Verify backend is running:

      curl http://<BACKEND_HOST_OR_IP>:8000/api/health

B. MQTT connection errors
- Check broker service:

      sudo systemctl status mosquitto

- Test publish and subscribe locally:

      mosquitto_sub -h 127.0.0.1 -t test/topic -v
      mosquitto_pub -h 127.0.0.1 -t test/topic -m hello

C. 401 errors from gateway API calls
- Confirm header mismatch fix is applied
- Confirm DEVICE_SERVICE_TOKEN exactly matches backend setting

D. No dedup
- Confirm Redis is running:

      sudo systemctl status redis-server

## 12. Hardening Recommendations (Important)

For production-like use:
1. Replace all default secrets with strong random values.
2. Disable anonymous MQTT access and configure username/password or certificates.
3. Use HTTPS for backend URL if accessible over untrusted networks.
4. Run backend without auto-reload mode.
5. Restrict firewall rules so only required ports are exposed.

## 13. Quick Verification Checklist

- Gateway service is active in systemd
- No repeated 401 in gateway logs
- MQTT gateway/health topic receives messages
- Backend receives heartbeat successfully
- Attendance records are being inserted from gateway traffic

If all are true, your Pi 4 gateway setup is complete.
