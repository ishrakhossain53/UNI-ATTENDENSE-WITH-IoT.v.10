# ESP32 Attendance Device Setup Guide

This guide explains how to set up a physical ESP32 attendance device for this project.

It is based on the current project protocol used by:
- attendance device simulator
- gateway service
- backend API

## 1. Scope and Architecture

Your ESP32 device should do five things:
1. Connect to Wi-Fi
2. Connect to MQTT broker
3. Subscribe for template downlink
4. Publish encrypted attendance uplink
5. Publish template sync acknowledgements

MQTT flow:
- Publish attendance to: attendance/uplink/<DEVICE_ID>
- Subscribe template downlink: templates/downlink/<DEVICE_ID>
- Publish template ACK: templates/ack/<DEVICE_ID>

## 2. Prerequisites

Hardware:
- ESP32 board (ESP32-S3 preferred)
- UART fingerprint module (example class: R307 / R503)
- Stable power source
- USB cable for flashing/debug

Backend stack running:
- MQTT broker
- Gateway service
- Backend API

You must know these values:
- WIFI_SSID
- WIFI_PASSWORD
- MQTT_BROKER
- MQTT_PORT
- DEVICE_ID (example: ESP32_CLASSROOM_101)
- DEVICE_SERVICE_TOKEN
- AES_KEY

## 3. Hardware Wiring

Typical UART wiring (check your module datasheet):
- Fingerprint TX -> ESP32 RX
- Fingerprint RX -> ESP32 TX
- VCC -> module required voltage
- GND -> ESP32 GND

Important:
- Verify UART logic level compatibility (3.3V logic expected by ESP32).
- Do not assume all modules tolerate 5V logic on UART pins.

## 4. Firmware Environment

Choose one:
- Arduino IDE
- PlatformIO

Install required libraries:
- WiFi
- PubSubClient (MQTT)
- ArduinoJson
- AES-GCM-compatible crypto library for ESP32
- Fingerprint module driver library compatible with your sensor

## 5. Device Configuration Block

Define these in firmware (constants or secure config storage):

- WIFI_SSID
- WIFI_PASSWORD
- MQTT_BROKER
- MQTT_PORT
- DEVICE_ID
- AES_KEY
- FIRMWARE_VERSION

Use the same AES key used by backend and gateway.

## 6. MQTT Setup

At startup:
1. Connect Wi-Fi
2. Connect MQTT
3. Subscribe to templates/downlink/<DEVICE_ID>

Reconnection strategy:
- If Wi-Fi drops, reconnect Wi-Fi first, then MQTT
- Retry with increasing delay

## 7. Attendance Uplink Message Format

When fingerprint match is successful, publish to:
- attendance/uplink/<DEVICE_ID>

Envelope JSON (MQTT payload):

{
  "device_eui": "ESP32_CLASSROOM_101",
  "fcnt": 1234,
  "rssi": -80,
  "snr": 7.5,
  "payload_encrypted": "<base64-ciphertext>",
  "nonce": "<base64-12-byte-nonce>",
  "tag": "<base64-16-byte-tag>"
}

Encrypted plaintext JSON (inside payload_encrypted):

{
  "device_id": "ESP32_CLASSROOM_101",
  "student_id": "<student-uuid>",
  "classroom_id": "ESP32_CLASSROOM_101",
  "timestamp": "2026-04-25T10:15:00Z",
  "match_score": 93,
  "battery_pct": 88,
  "firmware_version": "1.0.0"
}

Notes:
- nonce must be unique per encryption operation.
- tag is the AES-GCM auth tag.
- all encrypted fields are base64 strings in JSON.

## 8. Template Downlink Handling

Device subscribes:
- templates/downlink/<DEVICE_ID>

Incoming payload contains encrypted template envelope.

Device steps:
1. Parse envelope JSON
2. Decode base64 payload_encrypted, nonce, tag
3. Decrypt with AES key
4. Extract student_id and device_slot
5. Save mapping locally (student_id -> device_slot)

## 9. Template ACK Message

After successful template sync, publish ACK to:
- templates/ack/<DEVICE_ID>

ACK JSON:

{
  "device_id": "ESP32_CLASSROOM_101",
  "template_id": "<template-uuid>",
  "status": "synced"
}

## 10. Flash and Bring-up

1. Build firmware
2. Flash ESP32
3. Open serial monitor
4. Confirm logs show:
- Wi-Fi connected
- MQTT connected
- subscribed to templates/downlink/<DEVICE_ID>

## 11. End-to-End Verification

1. Enroll a student from admin dashboard
2. Confirm gateway publishes template downlink
3. Confirm ESP32 receives and ACKs template
4. Scan enrolled fingerprint
5. Confirm gateway receives attendance uplink
6. Confirm backend stores attendance
7. Confirm frontend live attendance updates

## 12. Troubleshooting

A. No MQTT connection
- Verify broker IP/port reachable from ESP32 network
- Verify SSID/password

B. Decryption failures
- AES key mismatch across device/gateway/backend
- Incorrect nonce/tag extraction

C. No attendance in backend
- Topic mismatch (must be attendance/uplink/<DEVICE_ID>)
- Envelope field names not matching expected format

D. Enrollment sync not working
- Subscription topic mismatch
- ACK topic mismatch

E. 401 from gateway/backend integration
- Check device token and gateway header handling consistency

## 13. Security Recommendations

1. Do not hardcode production secrets in plain firmware when possible.
2. Rotate DEVICE_SERVICE_TOKEN and AES_KEY periodically.
3. Use authenticated MQTT in production (avoid anonymous broker mode).
4. Restrict network access by VLAN/firewall where possible.

## 14. Deployment Checklist

- [ ] ESP32 boots and reconnects after power loss
- [ ] MQTT reconnect logic is stable
- [ ] Template downlink and ACK are confirmed
- [ ] Attendance uplink payload matches expected format
- [ ] AES encryption/decryption tested with real data
- [ ] Device clock/timestamp handling is correct
- [ ] End-to-end scan appears in dashboard

If all boxes are checked, your ESP32 attendance device integration is ready.
