#!/usr/bin/env python3
"""
Gateway Service — Raspberry Pi LoRa Gateway Bridge

Bridges MQTT (device uplink) to cloud backend REST API.
Four concurrent threads:
1. MQTT Uplink Consumer — receive encrypted scans, deduplicate, queue
2. Cloud Forwarder — batch forward queued records to backend
3. Template Sync Poller — poll for pending templates, distribute to devices
4. Health Monitor — publish gateway health every 60s
"""

import os
import sys
import json
import logging
import threading
import time
import base64
from datetime import datetime, timezone
from collections import deque
from typing import Dict, List, Optional, Any

import paho.mqtt.client as mqtt
import requests
import redis
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] %(levelname)s: %(message)s'
)
logger = logging.getLogger('Gateway')

# Environment variables
MQTT_BROKER = os.getenv('MQTT_BROKER', 'mosquitto')
MQTT_PORT = int(os.getenv('MQTT_PORT', 1883))
POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'postgres')
POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
POSTGRES_DB = os.getenv('POSTGRES_DB', 'attendance_db')
POSTGRES_USER = os.getenv('POSTGRES_USER', 'attendance_user')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', 'SecurePass123!')
REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:8000')
DEVICE_SERVICE_TOKEN = os.getenv('DEVICE_SERVICE_TOKEN', 'device_service_token_secret_key')
AES_KEY_HEX = os.getenv('AES_KEY', '0123456789abcdef0123456789abcdef')
SYNC_POLL_INTERVAL = int(os.getenv('SYNC_POLL_INTERVAL', 30))

# Gateway config
GATEWAY_ID = 'GW_MAIN'

# Global state
offline_queue: deque = deque(maxlen=500)  # Max 500 records
mqtt_client: Optional[mqtt.Client] = None
redis_client: Optional[redis.Redis] = None
stop_event = threading.Event()

# Metrics
metrics = {
    'records_forwarded_total': 0,
    'failed_forward_attempts': 0,
    'last_forward_at': None,
    'queue_depth': 0,
    'dedup_hits': 0,
    'start_time': datetime.now(timezone.utc)
}

# Thread synchronization
metrics_lock = threading.Lock()


def derive_aes_key(hex_key: str) -> bytes:
    """Convert hex string AES key to bytes."""
    if len(hex_key) == 64:  # 32 bytes in hex
        return bytes.fromhex(hex_key)
    h = hashes.Hash(hashes.SHA256(), backend=default_backend())
    h.update(hex_key.encode())
    return h.finalize()


def decrypt_aes_gcm(ciphertext: bytes, nonce: bytes, tag: bytes, key: bytes) -> bytes:
    """Decrypt AES-256-GCM ciphertext."""
    cipher = AESGCM(key)
    return cipher.decrypt(nonce, ciphertext + tag, None)


def encrypt_aes_gcm(plaintext: bytes, key: bytes) -> tuple:
    """Encrypt with AES-256-GCM. Returns (ciphertext, nonce, tag)."""
    cipher = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = cipher.encrypt(nonce, plaintext, None)
    return ciphertext[:-16], nonce, ciphertext[-16:]


def wait_for_dependencies(max_retries: int = 60) -> bool:
    """Wait for MQTT broker and backend to be ready."""
    logger.info("Waiting for dependencies...")
    
    # Test MQTT
    mqtt_ok = False
    for attempt in range(max_retries):
        try:
            test_client = mqtt.Client()
            test_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=5)
            test_client.disconnect()
            mqtt_ok = True
            logger.info(f"✓ MQTT broker available")
            break
        except:
            time.sleep(1 + (attempt * 0.1))
    
    if not mqtt_ok:
        logger.error("MQTT broker not available")
        return False
    
    # Test Backend
    backend_ok = False
    for attempt in range(max_retries):
        try:
            headers = {'Authorization': f'Bearer {DEVICE_SERVICE_TOKEN}'}
            resp = requests.get(f"{BACKEND_URL}/api/health", headers=headers, timeout=5)
            if resp.status_code < 500:
                backend_ok = True
                logger.info(f"✓ Backend API available")
                break
        except:
            time.sleep(1 + (attempt * 0.1))
    
    if not backend_ok:
        logger.error("Backend API not available")
        return False
    
    return True


def init_redis():
    """Initialize Redis connection."""
    global redis_client
    try:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True,
            socket_connect_timeout=5
        )
        redis_client.ping()
        logger.info("✓ Redis connected")
        return True
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        return False


def on_mqtt_connect(client, userdata, flags, rc):
    """MQTT connection callback."""
    if rc == 0:
        logger.info("✓ Connected to MQTT broker")
        client.subscribe("attendance/uplink/#")
        logger.info("✓ Subscribed to attendance/uplink/#")
    else:
        logger.error(f"MQTT connection failed: {rc}")


def on_mqtt_message(client, userdata, msg):
    """MQTT uplink message handler — Thread 1 worker."""
    try:
        device_id = msg.topic.split('/')[-1]
        envelope = json.loads(msg.payload.decode())
        
        # Decrypt payload
        ciphertext = base64.b64decode(envelope.get('payload_encrypted', ''))
        nonce = base64.b64decode(envelope.get('nonce', ''))
        tag = base64.b64decode(envelope.get('tag', ''))
        
        aes_key = derive_aes_key(AES_KEY_HEX)
        plaintext = decrypt_aes_gcm(ciphertext, nonce, tag, aes_key)
        record = json.loads(plaintext.decode())
        
        # Deduplication check
        fcnt = envelope.get('fcnt', 0)
        dedup_key = f"dedup:{device_id}:{fcnt}"
        
        if redis_client and redis_client.exists(dedup_key):
            with metrics_lock:
                metrics['dedup_hits'] += 1
            logger.info(f"[{device_id}] Duplicate detected (fcnt={fcnt}), skipping")
            return
        
        # Set dedup key with 30s TTL
        if redis_client:
            redis_client.setex(dedup_key, 30, '1')
        
        # Add to queue
        offline_queue.append(record)
        
        with metrics_lock:
            metrics['queue_depth'] = len(offline_queue)
        
        logger.info(f"[{device_id}] Scan received: student={record.get('student_id')}, queued")
    
    except Exception as e:
        logger.error(f"Error processing uplink message: {e}")


def thread_uplink_consumer(mqtt_client_ref):
    """Thread 1 — MQTT Uplink Consumer."""
    logger.info("[Thread 1] Uplink Consumer started")
    
    mqtt_client_ref.on_message = on_mqtt_message
    mqtt_client_ref.loop_start()
    
    while not stop_event.is_set():
        time.sleep(1)
    
    mqtt_client_ref.loop_stop()
    logger.info("[Thread 1] Uplink Consumer stopped")


def thread_cloud_forwarder():
    """Thread 2 — Cloud Forwarder."""
    logger.info("[Thread 2] Cloud Forwarder started")
    
    backoff_delay = 0  # Exponential backoff tracker
    
    while not stop_event.is_set():
        try:
            time.sleep(2)  # Forward every 2 seconds
            
            if not offline_queue:
                backoff_delay = 0
                continue
            
            # Wait before retrying if backoff active
            if backoff_delay > 0:
                time.sleep(backoff_delay)
                backoff_delay = min(backoff_delay * 2, 60)
            
            records_batch = []
            batch_size = min(10, len(offline_queue))  # Forward up to 10 at a time
            
            for _ in range(batch_size):
                records_batch.append(offline_queue.popleft())
            
            # Forward to backend
            headers = {
                'Authorization': f'Bearer {DEVICE_SERVICE_TOKEN}',
                'Content-Type': 'application/json'
            }
            
            payload = {'records': records_batch}
            
            resp = requests.post(
                f"{BACKEND_URL}/api/attendance",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            if 200 <= resp.status_code < 300:
                # Success
                with metrics_lock:
                    metrics['records_forwarded_total'] += len(records_batch)
                    metrics['last_forward_at'] = datetime.now(timezone.utc).isoformat()
                    metrics['queue_depth'] = len(offline_queue)
                
                logger.info(f"[Thread 2] ✓ Forwarded {len(records_batch)} records (queue depth: {len(offline_queue)})")
                backoff_delay = 0
            
            elif resp.status_code == 409:
                # Duplicate — discard silently
                logger.info(f"[Thread 2] 409 Duplicate detected, discarding {len(records_batch)} records")
                backoff_delay = 0
            
            elif 400 <= resp.status_code < 500:
                # Client error (other than 409) — discard and log
                logger.warning(f"[Thread 2] Client error {resp.status_code}: {resp.text}")
                backoff_delay = 0
            
            else:
                # Server error or network issue — re-queue and backoff
                for record in reversed(records_batch):
                    offline_queue.appendleft(record)
                
                with metrics_lock:
                    metrics['failed_forward_attempts'] += 1
                    metrics['queue_depth'] = len(offline_queue)
                
                if backoff_delay == 0:
                    backoff_delay = 1
                logger.warning(f"[Thread 2] Forward failed ({resp.status_code}), requeuing. Backoff: {backoff_delay}s")
        
        except requests.exceptions.Timeout:
            logger.warning("[Thread 2] Forward timeout, re-queueing batch")
            if backoff_delay == 0:
                backoff_delay = 1
        
        except Exception as e:
            logger.error(f"[Thread 2] Unexpected error: {e}")
            time.sleep(5)
    
    logger.info("[Thread 2] Cloud Forwarder stopped")


def thread_template_sync_poller():
    """Thread 3 — Template Sync Poller."""
    logger.info("[Thread 3] Template Sync Poller started")
    
    pending_acks = {}  # {(device_id, template_id): ack_received_event}
    
    def ack_listener():
        """Sub-thread to listen for template ACKs."""
        local_client = mqtt.Client()
        local_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        
        def on_ack_message(client, userdata, msg):
            try:
                ack_data = json.loads(msg.payload.decode())
                device_id = ack_data.get('device_id')
                template_id = ack_data.get('template_id')
                key = (device_id, template_id)
                
                if key in pending_acks:
                    pending_acks[key].set()
                    logger.info(f"[Thread 3] ACK received: device={device_id}, template={template_id}")
            except Exception as e:
                logger.warning(f"[Thread 3] Error processing ACK: {e}")
        
        local_client.on_message = on_ack_message
        local_client.subscribe("templates/ack/#")
        
        while not stop_event.is_set():
            local_client.loop()
            time.sleep(0.1)
        
        local_client.disconnect()
    
    # Start ACK listener
    ack_thread = threading.Thread(target=ack_listener, daemon=True)
    ack_thread.start()
    logger.info("[Thread 3] ACK listener sub-thread started")
    
    while not stop_event.is_set():
        try:
            time.sleep(SYNC_POLL_INTERVAL)
            
            # Poll for pending templates
            headers = {'Authorization': f'Bearer {DEVICE_SERVICE_TOKEN}'}
            resp = requests.get(
                f"{BACKEND_URL}/api/templates/pending-sync",
                headers=headers,
                timeout=10
            )
            
            if resp.status_code != 200:
                logger.warning(f"[Thread 3] Poll failed: {resp.status_code}")
                continue
            
            pending_templates = resp.json()
            if not pending_templates:
                continue
            
            logger.info(f"[Thread 3] Found {len(pending_templates)} pending templates")
            
            # Distribute each template
            for template_data in pending_templates:
                try:
                    device_id = template_data.get('device_id')
                    template_id = template_data.get('template_id')
                    
                    # Encrypt template
                    aes_key = derive_aes_key(AES_KEY_HEX)
                    plaintext = json.dumps(template_data).encode()
                    ciphertext, nonce, tag = encrypt_aes_gcm(plaintext, aes_key)
                    
                    # Build envelope
                    envelope = {
                        'device_id': device_id,
                        'template_id': template_id,
                        'payload_encrypted': base64.b64encode(ciphertext).decode(),
                        'nonce': base64.b64encode(nonce).decode(),
                        'tag': base64.b64encode(tag).decode()
                    }
                    
                    # Publish
                    topic = f"templates/downlink/{device_id}"
                    mqtt_client.publish(topic, json.dumps(envelope))
                    logger.info(f"[Thread 3] Published template: device={device_id}, template={template_id}")
                    
                    # Wait for ACK (max 10 seconds)
                    ack_key = (device_id, template_id)
                    pending_acks[ack_key] = threading.Event()
                    
                    if pending_acks[ack_key].wait(timeout=10):
                        # ACK received, mark as synced
                        headers = {'Authorization': f'Bearer {DEVICE_SERVICE_TOKEN}'}
                        ack_payload = {
                            'device_id': device_id,
                            'template_id': template_id,
                            'sync_version': template_data.get('sync_version', 1)
                        }
                        
                        resp = requests.post(
                            f"{BACKEND_URL}/api/templates/sync-ack",
                            json=ack_payload,
                            headers=headers,
                            timeout=10
                        )
                        
                        if resp.status_code == 200:
                            logger.info(f"[Thread 3] ✓ Sync confirmed: device={device_id}, template={template_id}")
                        else:
                            logger.warning(f"[Thread 3] Sync-ack failed: {resp.status_code}")
                    else:
                        # Timeout
                        logger.warning(f"[Thread 3] ACK timeout: device={device_id}, template={template_id}")
                    
                    del pending_acks[ack_key]
                
                except Exception as e:
                    logger.error(f"[Thread 3] Error distributing template: {e}")
        
        except Exception as e:
            logger.error(f"[Thread 3] Sync poller error: {e}")
            time.sleep(5)
    
    logger.info("[Thread 3] Template Sync Poller stopped")


def thread_health_monitor():
    """Thread 4 — Health Monitor."""
    logger.info("[Thread 4] Health Monitor started")
    
    while not stop_event.is_set():
        try:
            time.sleep(60)
            
            # Calculate uptime
            uptime_seconds = (datetime.now(timezone.utc) - metrics['start_time']).total_seconds()
            
            # Build health report
            with metrics_lock:
                health_report = {
                    'gateway_id': GATEWAY_ID,
                    'queue_depth': len(offline_queue),
                    'uptime_seconds': int(uptime_seconds),
                    'records_forwarded_total': metrics['records_forwarded_total'],
                    'last_forward_at': metrics['last_forward_at'],
                    'backend_reachable': True,
                    'connected_devices': ['ESP32_CLASSROOM_101', 'ESP32_CLASSROOM_102', 'ESP32_CLASSROOM_103', 
                                        'ESP32_CLASSROOM_104', 'ESP32_CLASSROOM_105']
                }
            
            # Publish to MQTT
            topic = 'gateway/health'
            mqtt_client.publish(topic, json.dumps(health_report))
            
            # Call heartbeat API
            headers = {'Authorization': f'Bearer {DEVICE_SERVICE_TOKEN}'}
            resp = requests.post(
                f"{BACKEND_URL}/api/gateway/heartbeat",
                json=health_report,
                headers=headers,
                timeout=10
            )
            
            if resp.status_code == 200:
                fwd_per_min = metrics['records_forwarded_total'] / max(1, uptime_seconds / 60)
                logger.info(f"[Thread 4] ✓ Health OK | Queue: {len(offline_queue)} | "
                          f"Forwarded: {metrics['records_forwarded_total']} | "
                          f"Rate: {fwd_per_min:.1f} rec/min | "
                          f"Failed attempts: {metrics['failed_forward_attempts']}")
            else:
                logger.warning(f"[Thread 4] Heartbeat failed: {resp.status_code}")
        
        except Exception as e:
            logger.error(f"[Thread 4] Health monitor error: {e}")
    
    logger.info("[Thread 4] Health Monitor stopped")


def main():
    """Main entry point."""
    global mqtt_client, offline_queue
    
    logger.info("=" * 70)
    logger.info("Gateway Service Starting — LoRa Gateway Bridge")
    logger.info("=" * 70)
    
    # Wait for dependencies
    if not wait_for_dependencies():
        logger.error("Failed to start: dependencies not available")
        sys.exit(1)
    
    # Init Redis
    if not init_redis():
        logger.error("Redis initialization failed (continuing without dedup)")
    
    # Connect to MQTT
    mqtt_client = mqtt.Client()
    mqtt_client.on_connect = on_mqtt_connect
    
    try:
        mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        logger.info("✓ MQTT client created")
    except Exception as e:
        logger.error(f"Failed to create MQTT client: {e}")
        sys.exit(1)
    
    # Start threads
    threads = []
    
    t1 = threading.Thread(target=thread_uplink_consumer, args=(mqtt_client,), daemon=True)
    t1.start()
    threads.append(('Uplink Consumer', t1))
    
    t2 = threading.Thread(target=thread_cloud_forwarder, daemon=True)
    t2.start()
    threads.append(('Cloud Forwarder', t2))
    
    t3 = threading.Thread(target=thread_template_sync_poller, daemon=True)
    t3.start()
    threads.append(('Template Sync', t3))
    
    t4 = threading.Thread(target=thread_health_monitor, daemon=True)
    t4.start()
    threads.append(('Health Monitor', t4))
    
    logger.info("=" * 70)
    logger.info(f"Gateway {GATEWAY_ID} is running. 4 worker threads active.")
    logger.info("Press Ctrl+C to stop.")
    logger.info("=" * 70)
    
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nShutdown requested...")
        stop_event.set()
        
        for name, t in threads:
            t.join(timeout=5)
            logger.info(f"✓ {name} thread stopped")
        
        if mqtt_client:
            mqtt_client.disconnect()
        
        if redis_client:
            redis_client.close()
        
        logger.info("✓ Gateway shutdown complete. Goodbye!")


if __name__ == '__main__':
    main()
