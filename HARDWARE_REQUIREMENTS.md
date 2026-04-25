# Hardware Requirements

This document lists all hardware needed to run the University Attendance with IoT system.

## 1. Overview

The project can be used in two modes:
1. Demo mode (with ESP32 emulator)
2. Real device mode (with physical ESP32 + fingerprint sensors)

The backend stack (PostgreSQL, Redis, MQTT broker, backend API, frontend) can run on one machine or server. The gateway is intended for a Raspberry Pi 4.

## 2. Minimum Hardware (Demo Mode)

Use this if you only want to run and test the complete software flow without physical scanners.

| Item | Quantity | Minimum Spec | Purpose |
|---|---:|---|---|
| Host machine (Linux/Windows/macOS) | 1 | 4 CPU cores, 8 GB RAM, 20 GB free SSD | Runs Docker services (DB, Redis, MQTT, backend, frontend, emulator) |
| Raspberry Pi 4 (optional in demo mode) | 0-1 | 2 GB RAM minimum (4 GB recommended) | Runs gateway service separately for realistic edge testing |
| Power supply for Pi 4 (if used) | 1 | Official 5V/3A USB-C | Stable gateway power |
| MicroSD card for Pi 4 (if used) | 1 | 32 GB Class 10 or better | Raspberry Pi OS and gateway runtime |
| Local network/router | 1 | Standard LAN/Wi-Fi | Connectivity between Pi, host, and devices |

## 3. Required Hardware (Real Device Mode)

Use this for physical classroom attendance collection.

| Item | Quantity | Recommended Spec | Purpose |
|---|---:|---|---|
| Backend host/server | 1 | 8 CPU cores, 16 GB RAM, 100 GB SSD | Runs database, broker, backend API, frontend |
| Raspberry Pi 4 (Gateway) | 1 | 4 GB or 8 GB RAM | Runs gateway bridge service 24/7 |
| Pi 4 power supply | 1 | 5V/3A USB-C (official) | Reliable power for gateway |
| MicroSD card (Pi 4) | 1 | 32 GB or 64 GB, Class 10/A1+ | OS, logs, service runtime |
| ESP32 dev boards | 1 per classroom | ESP32-S3 preferred | Classroom scanner controller |
| Fingerprint sensor modules | 1 per ESP32 | UART sensor compatible with ESP32 | Biometric capture and matching |
| ESP32 power adapters | 1 per ESP32 | 5V/2A | Power for each scanner unit |
| Device enclosure/case | 1 per ESP32 unit | Wall/table mount type | Physical protection in classroom |
| Network access points/switches | As needed | Stable Wi-Fi/LAN coverage | Device and gateway connectivity |
| Router/firewall appliance | 1 | Supports VLAN/firewall rules | Network segmentation and security |
| UPS (recommended) | 1-2 | 600 VA+ depending on load | Power backup for server/gateway |

## 4. Example Quantity for 5 Classrooms

If you deploy to 5 classrooms:

- Backend host/server: 1
- Raspberry Pi 4 gateway: 1
- ESP32 boards: 5
- Fingerprint modules: 5
- ESP32 power adapters: 5
- Device enclosures: 5
- Pi power supply: 1
- MicroSD card for Pi: 1
- Router/switch/AP: based on site size

## 5. Optional but Strongly Recommended Hardware

| Item | Quantity | Why It Helps |
|---|---:|---|
| External SSD for backend host | 1 | Better DB performance and durability than SD cards |
| Spare ESP32 units | 1-2 | Fast replacement if a classroom unit fails |
| Spare fingerprint modules | 1-2 | Reduces maintenance downtime |
| PoE switch + adapters | As needed | Cleaner power/network setup for fixed installations |
| Dedicated monitor/keyboard for Pi setup | 1 (temporary) | Easier first-time configuration |

## 6. Environmental and Physical Requirements

- Reliable power with surge protection
- Stable network coverage in all classrooms
- Secure mounting to prevent tampering
- Reasonable indoor temperature and ventilation
- Physical access controls for backend host and gateway

## 7. Hardware Checklist Before Go-Live

- Backend host prepared and stress-tested
- Raspberry Pi gateway running continuously
- All ESP32 units powered and reachable
- Fingerprint sensors calibrated and tested
- UPS tested for failover behavior
- Network segmentation/firewall rules validated
- Spare units available for quick replacement

## 8. Notes

- The current repository includes an ESP32 emulator, so physical ESP32 hardware is not required for software-only testing.
- For production deployment, physical scanner devices and power/network resilience are essential.
