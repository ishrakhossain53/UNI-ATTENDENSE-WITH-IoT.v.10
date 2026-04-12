#!/usr/bin/env python3
"""
ESP32 Classroom Fingerprint Scanner Emulator

Simulates 5 ESP32-S3 classroom units. Each unit:
1. Periodically publishes encrypted attendance scans over MQTT
2. Subscribes to template sync messages from gateway
3. Maintains offline queue if MQTT publish fails
"""

import os
import sys
import json
import logging
import threading
import time
import random
import base64
import hashlib
from datetime import datetime, timezone
from collections import deque
from typing import Dict, List, Optional, Tuple

import paho.mqtt.client as mqtt
import requests
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('ESP32')

# Environment variables
MQTT_BROKER = os.getenv('MQTT_BROKER', 'mosquitto')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:8000')
DEVICE_SERVICE_TOKEN = os.getenv('DEVICE_SERVICE_TOKEN', 'device_service_token_secret_key')
AES_KEY_HEX = os.getenv('AES_KEY', '0123456789abcdef0123456789abcdef')
SCAN_INTERVAL_MIN = int(os.getenv('ESP32_SCAN_INTERVAL_MIN', 10))
SCAN_INTERVAL_MAX = int(os.getenv('ESP32_SCAN_INTERVAL_MAX', 20))

# Global state
enrolled_students: Dict[str, Dict] = {}  # {student_id: {student_number, full_name}, ...}
device_templates: Dict[str, Dict] = {}   # {device_id: {student_id: template_slot}, ...}
offline_queue: Dict[str, deque] = {}    # {device_id: deque of messages}
mqtt_client: Optional[mqtt.Client] = None
stop_event = threading.Event()

# Device configurations
DEVICES = [
    {'id': 'ESP32_CLASSROOM_101', 'classroom': 'room_101', 'building': 'A'},
    {'id': 'ESP32_CLASSROOM_102', 'classroom': 'room_102', 'building': 'A'},
    {'id': 'ESP32_CLASSROOM_103', 'classroom': 'room_103', 'building': 'B'},
    {'id': 'ESP32_CLASSROOM_104', 'classroom': 'room_104', 'building': 'B'},
    {'id': 'ESP32_CLASSROOM_105', 'classroom': 'room_105', 'building': 'C'},
]


def derive_aes_key(hex_key: str) -> bytes:
    """Convert hex string AES key to bytes."""
    if len(hex_key) == 64:  # 32 bytes in hex
        return bytes.fromhex(hex_key)
    # Fallback: hash it
    h = hashes.Hash(hashes.SHA256(), backend=default_backend())
    h.update(hex_key.encode())
    return h.finalize()


def encrypt_aes_gcm(plaintext: bytes, key: bytes) -> Tuple[bytes, bytes, bytes]:
    """
    Encrypt plaintext with AES-256-GCM.
    Returns (ciphertext, nonce, tag)
    """
    cipher = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce
    ciphertext = cipher.encrypt(nonce, plaintext, None)
    # ciphertext includes the tag at the end
    return ciphertext[:-16], nonce, ciphertext[-16:]


def decrypt_aes_gcm(ciphertext: bytes, nonce: bytes, tag: bytes, key: bytes) -> bytes:
    """Decrypt AES-256-GCM ciphertext."""
    cipher = AESGCM(key)
    return cipher.decrypt(nonce, ciphertext + tag, None)


def wait_for_dependencies(max_retries: int = 60, delay: int = 1) -> bool:
    """
    Wait for MQTT broker and backend API to be ready.
    Uses exponential backoff.
    """
    logger.info("Waiting for dependencies...")
    
    # Test MQTT broker
    mqtt_ready = False
    for attempt in range(max_retries):
        try:
            test_client = mqtt.Client()
            test_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=5)
            test_client.disconnect()
            mqtt_ready = True
            logger.info(f"✓ MQTT broker available at {MQTT_BROKER}:{MQTT_PORT}")
            break
        except Exception as e:
            logger.debug(f"MQTT not ready (attempt {attempt+1}/{max_retries}): {e}")
            time.sleep(delay + (attempt * 0.1))  # Light exponential backoff
    
    if not mqtt_ready:
        logger.error("MQTT broker not available after max retries")
        return False
    
    # Test Backend API
    backend_ready = False
    for attempt in range(max_retries):
        try:
            headers = {'Authorization': f'Bearer {DEVICE_SERVICE_TOKEN}'}
            resp = requests.get(f"{BACKEND_URL}/api/students/enrolled", headers=headers, timeout=5)
            if resp.status_code in (200, 401, 403):  # API responds
                backend_ready = True
                logger.info(f"✓ Backend API available at {BACKEND_URL}")
                break
        except Exception as e:
            logger.debug(f"Backend not ready (attempt {attempt+1}/{max_retries}): {e}")
            time.sleep(delay + (attempt * 0.1))
    
    if not backend_ready:
        logger.error("Backend API not available after max retries")
        return False
    
    return True


def fetch_enrolled_students(retry_count: int = 5) -> bool:
    """
    Fetch list of enrolled students from backend.
    Retry with exponential backoff.
    """
    global enrolled_students
    
    headers = {'Authorization': f'Bearer {DEVICE_SERVICE_TOKEN}'}
    
    for attempt in range(retry_count):
        try:
            resp = requests.get(
                f"{BACKEND_URL}/api/students/enrolled",
                headers=headers,
                timeout=10
            )
            resp.raise_for_status()
            
            # Response assumed to be list of students
            students_data = resp.json()
            if isinstance(students_data, list):
                enrolled_students = {s.get('student_id'): {
                    'student_number': s.get('student_number'),
                    'full_name': s.get('full_name')
                } for s in students_data}
            else:
                logger.error(f"Unexpected response format: {students_data}")
                return False
            
            logger.info(f"✓ Fetched {len(enrolled_students)} enrolled students")
            return True
        
        except Exception as e:
            logger.warning(f"Failed to fetch enrolled students (attempt {attempt+1}/{retry_count}): {e}")
            time.sleep(2 ** attempt)
    
    logger.error("Could not fetch enrolled students after retries")
    return False


def fetch_device_templates(device_id: str, retry_count: int = 3) -> bool:
    """
    Fetch fingerprint templates for a device.
    Response: {student_id: template_slot, ...}
    """
    global device_templates
    
    headers = {'Authorization': f'Bearer {DEVICE_SERVICE_TOKEN}'}
    
    for attempt in range(retry_count):
        try:
            resp = requests.get(
                f"{BACKEND_URL}/api/templates/device/{device_id}",
                headers=headers,
                timeout=10
            )
            resp.raise_for_status()
            
            templates = resp.json()
            if isinstance(templates, dict):
                device_templates[device_id] = templates
                logger.info(f"[{device_id}] Fetched {len(templates)} templates")
                return True
            else:
                logger.error(f"[{device_id}] Unexpected template response: {templates}")
                return False
        
        except Exception as e:
            logger.warning(f"[{device_id}] Failed to fetch templates (attempt {attempt+1}/{retry_count}): {e}")
            time.sleep(2 ** attempt)
    
    logger.warning(f"[{device_id}] Could not fetch templates, proceeding with empty")
    device_templates[device_id] = {}
    return True


def on_mqtt_connect(client, userdata, flags, rc):
    """MQTT connection callback."""
    if rc == 0:
        logger.info("✓ Connected to MQTT broker")
        # Subscribe to template sync messages for all devices
        for device in DEVICES:
            topic = f"templates/downlink/{device['id']}"
            client.subscribe(topic)
            logger.info(f"[{device['id']}] Subscribed to {topic}")
    else:
        logger.error(f"MQTT connection failed with code {rc}")


def on_mqtt_disconnect(client, userdata, rc):
    """MQTT disconnection callback."""
    if rc == 0:
        logger.info("Clean disconnect from MQTT")
    else:
        logger.warning(f"Unexpected disconnect from MQTT (code {rc})")


def on_mqtt_message(client, userdata, msg):
    """MQTT message callback for template sync."""
    device_id = None
    for device in DEVICES:
        if msg.topic == f"templates/downlink/{device['id']}":
            device_id = device['id']
            break
    
    if not device_id:
        logger.warning(f"Received message on unknown topic: {msg.topic}")
        return
    
    try:
        envelope = json.loads(msg.payload.decode())
        payload_encrypted = base64.b64decode(envelope.get('payload_encrypted', ''))
        nonce = base64.b64decode(envelope.get('nonce', ''))
        tag = base64.b64decode(envelope.get('tag', ''))
        
        # Decrypt
        aes_key = derive_aes_key(AES_KEY_HEX)
        template_data = decrypt_aes_gcm(payload_encrypted, nonce, tag, aes_key)
        template_json = json.loads(template_data.decode())
        
        # Update local templates
        student_id = template_json.get('student_id')
        template_slot = template_json.get('device_slot', 0)
        
        if device_id not in device_templates:
            device_templates[device_id] = {}
        device_templates[device_id][student_id] = template_slot
        
        logger.info(f"[{device_id}] ✓ Template synced: student={student_id}, slot={template_slot}")
        
        # Publish ACK
        ack_payload = json.dumps({
            'device_id': device_id,
            'template_id': template_json.get('template_id'),
            'status': 'synced'
        }).encode()
        
        mqtt_client.publish(f"templates/ack/{device_id}", ack_payload)
        logger.info(f"[{device_id}] Published sync ACK")
    
    except Exception as e:
        logger.error(f"[{device_id}] Error processing template sync: {e}")


def publish_attendance(device_id: str, student_id: str, client: mqtt.Client) -> bool:
    """
    Construct and publish encrypted attendance record to MQTT.
    Returns True if publish successful, False if queued offline.
    """
    try:
        # Simulate scan
        match_score = random.randint(85, 99) if random.random() > 0.05 else 0
        
        # Build attendance payload
        attendance_record = {
            'device_id': device_id,
            'student_id': student_id,
            'classroom_id': device_id,  # backend resolves UUID via device_id fallback
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'match_score': match_score,
            'battery_pct': random.randint(75, 100),
            'firmware_version': '1.2.3'
        }
        
        # Encrypt payload
        aes_key = derive_aes_key(AES_KEY_HEX)
        plaintext = json.dumps(attendance_record).encode()
        ciphertext, nonce, tag = encrypt_aes_gcm(plaintext, aes_key)
        
        # Build envelope
        envelope = {
            'device_eui': device_id,
            'fcnt': random.randint(1000, 9999),
            'rssi': random.randint(-95, -70),
            'snr': round(random.uniform(3.0, 12.0), 1),
            'payload_encrypted': base64.b64encode(ciphertext).decode(),
            'nonce': base64.b64encode(nonce).decode(),
            'tag': base64.b64encode(tag).decode()
        }
        
        topic = f"attendance/uplink/{device_id}"
        result = client.publish(topic, json.dumps(envelope), qos=1)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            status = 'success' if match_score > 0 else 'no_match'
            logger.info(f"[{device_id}] Scan: student={student_id}, match={match_score}, status={status}")
            return True
        else:
            logger.warning(f"[{device_id}] Publish failed with code {result.rc}, queueing offline")
            # Queue for later
            if device_id not in offline_queue:
                offline_queue[device_id] = deque(maxlen=500)
            offline_queue[device_id].append(envelope)
            return False
    
    except Exception as e:
        logger.error(f"[{device_id}] Error publishing attendance: {e}")
        return False


def device_scan_loop(device_config: Dict, mqtt_client_ref):
    """
    Main loop for a single device.
    Periodically publishes attendance scans.
    """
    device_id = device_config['id']
    logger.info(f"[{device_id}] Device thread started")
    
    while not stop_event.is_set():
        try:
            # Wait for next scan interval
            interval = random.randint(SCAN_INTERVAL_MIN, SCAN_INTERVAL_MAX)
            time.sleep(interval)
            
            if not enrolled_students:
                logger.debug(f"[{device_id}] No enrolled students available")
                continue
            
            # Pick random student
            student_id = random.choice(list(enrolled_students.keys()))
            
            # Publish scan
            publish_attendance(device_id, student_id, mqtt_client_ref)
            
            # Flush offline queue if any
            if device_id in offline_queue and offline_queue[device_id]:
                queue = offline_queue[device_id]
                batch_size = min(5, len(queue))
                for _ in range(batch_size):
                    envelope = queue.popleft()
                    topic = f"attendance/uplink/{device_id}"
                    result = mqtt_client_ref.publish(topic, json.dumps(envelope), qos=1)
                    if result.rc == mqtt.MQTT_ERR_SUCCESS:
                        logger.info(f"[{device_id}] Flushed offline scan")
                    else:
                        queue.appendleft(envelope)  # Re-queue if failed
                        break
        
        except Exception as e:
            logger.error(f"[{device_id}] Error in scan loop: {e}")
            time.sleep(5)


def main():
    """Main entry point."""
    global mqtt_client, stop_event
    
    logger.info("=" * 60)
    logger.info("ESP32 Classroom Scanner Emulator Starting")
    logger.info("=" * 60)
    
    # Wait for dependencies
    if not wait_for_dependencies():
        logger.error("Failed to wait for dependencies")
        sys.exit(1)
    
    # Fetch enrolled students
    if not fetch_enrolled_students():
        logger.error("Failed to fetch enrolled students")
        sys.exit(1)
    
    # Fetch templates for each device
    for device in DEVICES:
        fetch_device_templates(device['id'])
    
    # Connect to MQTT
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_disconnect = on_mqtt_disconnect
    mqtt_client.on_message = on_mqtt_message
    
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        logger.info("✓ MQTT client started")
    except Exception as e:
        logger.error(f"Failed to connect to MQTT: {e}")
        sys.exit(1)
    
    # Initialize offline queues
    for device in DEVICES:
        offline_queue[device['id']] = deque(maxlen=500)
    
    # Start device simulation threads
    threads = []
    for device in DEVICES:
        t = threading.Thread(target=device_scan_loop, args=(device, mqtt_client), daemon=True)
        t.start()
        threads.append(t)
        logger.info(f"[{device['id']}] Simulation thread started")
    
    logger.info("=" * 60)
    logger.info("All devices running. Press Ctrl+C to stop.")
    logger.info("=" * 60)
    
    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nShutdown requested...")
        stop_event.set()
        
        # Wait for threads
        for t in threads:
            t.join(timeout=5)
        
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        logger.info("✓ All threads stopped. Goodbye!")


if __name__ == '__main__':
    main()
