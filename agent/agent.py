#!/usr/bin/env python3
"""
©AngelaMos | 2026
agent.py

Autonomous Server Log Ingestion Agent for Kali Linux / Debian

Monitors /var/log/auth.log, extracts security authentication events
(SSH failed logins, successful logins, sudo privilege escalations),
spools events locally in a durable SQLite database for offline resilience,
and reliably ships events and heartbeats to the SIEM Dashboard.

Usage:
  sudo python3 agent.py --config config.yaml
"""

import argparse
import logging
import os
import re
import socket
import sqlite3
import sys
import threading
import time
import uuid
from datetime import datetime, UTC
from typing import Any

try:
    import requests
    import yaml
    import psutil
except ImportError as exc:
    print(f"[!] Missing required library: {exc}")
    print("[!] Run: pip install -r requirements.txt")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("siem-agent")

# Regex patterns for Linux auth.log parsing
SSH_FAILED_PATTERN = re.compile(
    r"Failed password for (?:invalid user )?(\S+) from (\S+) port (\d+) ssh2"
)
SSH_ACCEPTED_PATTERN = re.compile(
    r"Accepted (?:password|publickey) for (\S+) from (\S+) port (\d+) ssh2"
)
SSH_INVALID_USER_PATTERN = re.compile(
    r"Invalid user (\S+) from (\S+) port (\d+)"
)
SUDO_COMMAND_PATTERN = re.compile(
    r"sudo:\s+(\S+)\s+:.*COMMAND=(.+)"
)


class SpoolQueue:
    """
    Durable local SQLite queue for event spooling during network interruptions
    """
    def __init__(self, db_path: str = "spool.db") -> None:
        self.db_path = db_path
        self._lock = threading.Lock()
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS event_spool (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_id TEXT UNIQUE,
                        event_data TEXT,
                        created_at REAL,
                        attempts INTEGER DEFAULT 0
                    )
                    """
                )
                conn.commit()

    def enqueue(self, event_id: str, event_data_json: str) -> bool:
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute(
                        "INSERT OR IGNORE INTO event_spool (event_id, event_data, created_at) VALUES (?, ?, ?)",
                        (event_id, event_data_json, time.time()),
                    )
                    conn.commit()
                return True
            except Exception as e:
                logger.error("Failed to enqueue event: %s", e)
                return False

    def dequeue_batch(self, limit: int = 50) -> list[tuple[int, str, str]]:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, event_id, event_data FROM event_spool ORDER BY id ASC LIMIT ?",
                    (limit,),
                )
                return cursor.fetchall()

    def delete_acknowledged(self, row_ids: list[int]) -> None:
        if not row_ids:
            return
        placeholders = ",".join("?" for _ in row_ids)
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    f"DELETE FROM event_spool WHERE id IN ({placeholders})",
                    row_ids,
                )
                conn.commit()

    def count(self) -> int:
        with self._lock:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM event_spool")
                return cursor.fetchone()[0]


class SiemAgent:
    """
    Main Agent coordinator managing tailing, spooling, and heartbeat workers
    """
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.siem_url = config.get("siem_url", "").rstrip("/")
        self.agent_id = config.get("agent_id", "")
        self.agent_token = config.get("agent_token", "")
        self.log_path = config.get("auth_log_path", "/var/log/auth.log")
        self.heartbeat_interval = int(config.get("heartbeat_interval", 30))
        self.verify_ssl = config.get("verify_ssl", True)
        self.agent_version = config.get("agent_version", "1.0.0")
        self.hostname = config.get("hostname") or socket.gethostname()

        self.spool = SpoolQueue(config.get("spool_db_path", "spool.db"))
        self._running = threading.Event()
        self._running.set()

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.agent_token}",
            "Content-Type": "application/json",
            "User-Agent": f"SiemAgent/{self.agent_version} ({sys.platform})",
        })

    def run(self) -> None:
        logger.info("Starting SIEM Log Agent for %s [ID: %s]", self.hostname, self.agent_id)
        logger.info("SIEM Gateway: %s", self.siem_url)
        logger.info("Monitoring Log: %s", self.log_path)

        heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
            name="agent-heartbeat",
        )
        spool_thread = threading.Thread(
            target=self._spool_sender_loop,
            daemon=True,
            name="agent-spool",
        )

        heartbeat_thread.start()
        spool_thread.start()

        try:
            self._tail_auth_log()
        except KeyboardInterrupt:
            logger.info("Shutdown requested by user")
        finally:
            self.stop()

    def stop(self) -> None:
        self._running.clear()
        logger.info("SIEM Log Agent stopped.")

    def _heartbeat_loop(self) -> None:
        """Periodically reports agent health and system telemetry"""
        url = f"{self.siem_url}/agents/heartbeat"
        while self._running.is_set():
            try:
                metrics = {
                    "cpu_percent": psutil.cpu_percent(interval=None),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage("/").percent,
                    "queue_depth": self.spool.count(),
                }
                payload = {
                    "agent_version": self.agent_version,
                    "metrics": metrics,
                }
                resp = self.session.post(
                    url,
                    json=payload,
                    timeout=10,
                    verify=self.verify_ssl,
                )
                if resp.status_code == 200:
                    logger.debug("Heartbeat acknowledged by SIEM")
                elif resp.status_code == 401:
                    logger.error("Authentication failed: agent token invalid or revoked!")
                else:
                    logger.warning("Heartbeat returned unexpected status: %d", resp.status_code)
            except requests.exceptions.RequestException as e:
                logger.warning("SIEM unreachable during heartbeat: %s", e)
            except Exception as e:
                logger.error("Unexpected error in heartbeat worker: %s", e)

            # Wait for interval or stop event
            self._running.wait(self.heartbeat_interval)

    def _spool_sender_loop(self) -> None:
        """Flushes enqueued security events to the SIEM with retry backoff"""
        url = f"{self.siem_url}/agents/ingest"
        backoff = 1.0

        while self._running.is_set():
            batch = self.spool.dequeue_batch(limit=25)
            if not batch:
                self._running.wait(1.0)
                continue

            ack_ids = []
            for row_id, event_id, event_data_json in batch:
                if not self._running.is_set():
                    break
                try:
                    resp = self.session.post(
                        url,
                        data=event_data_json,
                        timeout=10,
                        verify=self.verify_ssl,
                    )
                    # 201 Created or 200 Duplicate accepted
                    if resp.status_code in (200, 201):
                        ack_ids.append(row_id)
                        backoff = 1.0
                    elif resp.status_code == 401:
                        logger.critical("Agent credentials revoked or rejected by server!")
                        self._running.wait(10.0)
                    else:
                        logger.warning("Ingest API returned %d: %s", resp.status_code, resp.text)
                        break
                except requests.exceptions.RequestException:
                    # Connection dropped - backoff and retry
                    time.sleep(min(backoff, 30.0))
                    backoff = min(backoff * 1.5, 30.0)
                    break

            if ack_ids:
                self.spool.delete_acknowledged(ack_ids)
                logger.info("Forwarded %d events to SIEM (Remaining: %d)", len(ack_ids), self.spool.count())

    def _tail_auth_log(self) -> None:
        """Tails the system authentication log file and enqueues matches"""
        if not os.path.exists(self.log_path):
            logger.warning("Log file %s does not exist. Creating watcher...", self.log_path)
            while not os.path.exists(self.log_path) and self._running.is_set():
                time.sleep(2)

        try:
            with open(self.log_path, "r", encoding="utf-8", errors="ignore") as f:
                # Seek to end on startup so we only capture new events
                f.seek(0, os.SEEK_END)
                current_inode = os.fstat(f.fileno()).st_ino

                while self._running.is_set():
                    line = f.readline()
                    if line:
                        self._process_log_line(line.strip(), f.tell(), current_inode)
                    else:
                        # Check for log rotation
                        if os.path.exists(self.log_path):
                            new_inode = os.stat(self.log_path).st_ino
                            if new_inode != current_inode:
                                logger.info("Log rotation detected for %s. Re-opening...", self.log_path)
                                break
                        time.sleep(0.2)
        except PermissionError:
            logger.error("Permission denied reading %s. Please run as root / sudo.", self.log_path)
        except Exception as e:
            logger.error("Log reader encountered error: %s", e)

    def _process_log_line(self, line: str, offset: int, inode: int) -> None:
        """Extracts security events and generates unique event_id"""
        if not line:
            return

        event: dict[str, Any] | None = None

        # SSH Failed Login
        m = SSH_FAILED_PATTERN.search(line)
        if m:
            user, ip, port = m.groups()
            event = {
                "source_type": "auth",
                "event_type": "login_failure",
                "username": user,
                "source_ip": ip,
                "source_port": int(port),
                "dest_ip": self.config.get("local_ip", ""),
                "dest_port": 22,
                "hostname": self.hostname,
                "message": line,
            }
        else:
            # SSH Accepted Login
            m = SSH_ACCEPTED_PATTERN.search(line)
            if m:
                user, ip, port = m.groups()
                event = {
                    "source_type": "auth",
                    "event_type": "login_success",
                    "username": user,
                    "source_ip": ip,
                    "source_port": int(port),
                    "dest_ip": self.config.get("local_ip", ""),
                    "dest_port": 22,
                    "hostname": self.hostname,
                    "message": line,
                }
            else:
                # Invalid user probe
                m = SSH_INVALID_USER_PATTERN.search(line)
                if m:
                    user, ip, port = m.groups()
                    event = {
                        "source_type": "auth",
                        "event_type": "login_failure",
                        "username": user,
                        "source_ip": ip,
                        "source_port": int(port),
                        "hostname": self.hostname,
                        "message": line,
                    }
                else:
                    # Sudo execution
                    m = SUDO_COMMAND_PATTERN.search(line)
                    if m:
                        user, cmd = m.groups()
                        event = {
                            "source_type": "auth",
                            "event_type": "privilege_escalation",
                            "username": user,
                            "hostname": self.hostname,
                            "message": f"sudo command: {cmd.strip()}",
                        }

        if event:
            # Deterministic UUIDv5 prevents duplicates across re-reads of the same line
            event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{self.hostname}:{inode}:{offset}:{line}"))
            event["event_id"] = event_id
            event["timestamp"] = datetime.now(UTC).isoformat()
            event["agent_version"] = self.agent_version

            import json
            payload_json = json.dumps(event)
            self.spool.enqueue(event_id, payload_json)
            logger.info("Enqueued event: %s for user '%s'", event["event_type"], event.get("username", "unknown"))


def main() -> None:
    parser = argparse.ArgumentParser(description="SIEM Server Log Ingestion Agent")
    parser.add_argument("-c", "--config", default="config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"[!] Configuration file '{args.config}' not found.")
        print("[!] Copy config.yaml.example to config.yaml and configure your agent credentials.")
        sys.exit(1)

    with open(args.config, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not config.get("siem_url") or not config.get("agent_token"):
        print("[!] 'siem_url' and 'agent_token' are required in config.yaml.")
        sys.exit(1)

    agent = SiemAgent(config)
    agent.run()


if __name__ == "__main__":
    main()
