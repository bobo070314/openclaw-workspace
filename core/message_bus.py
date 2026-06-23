#!/usr/bin/env python
"""Message Bus — V5.0 Agent Nervous System.

SecAgent / OpsAgent / AnalystAgent communicate via JSONL bus.
Evolution Engine reads bus to coordinate multi-agent workflows.

V5.0: Added cross-platform file locking (msvcrt on Windows, fcntl on Unix)
to prevent concurrent-write corruption under multi-agent pressure.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

BUS_FILE = Path("D:/bobo/openclaw-foreign/.deploy/mbus.jsonl")
BUS_FILE.parent.mkdir(parents=True, exist_ok=True)


class MessageBus:
    def _write_locked(self, filepath, message):
        """Cross-platform locked write to prevent concurrent corruption."""
        with open(filepath, "a", encoding="utf-8") as f:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1024)
                f.write(message)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1024)
            else:
                import fcntl

                fcntl.flock(f, fcntl.LOCK_EX)
                f.write(message)
                fcntl.flock(f, fcntl.LOCK_UN)

    def emit(self, sender, receiver, msg_type, payload):
        event = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "sender": sender,
            "receiver": receiver,
            "type": msg_type,
            "payload": payload,
        }
        self._write_locked(BUS_FILE, json.dumps(event, ensure_ascii=False) + "\n")
        print(f"[BUS] {sender} -> {receiver}: {msg_type}")

    def listen(self, agent_name):
        if not BUS_FILE.exists():
            return []
        try:
            lines = [json.loads(l) for l in BUS_FILE.read_text(encoding="utf-8").strip().split("\n") if l]
            return [e for e in lines if e["receiver"] == agent_name or e["receiver"] == "*"]
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def last(self, agent_name, n=10):
        return self.listen(agent_name)[-n:]


bus = MessageBus()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Message Bus CLI")
    sub = parser.add_subparsers(dest="action")
    em = sub.add_parser("emit")
    em.add_argument("--sender", required=True)
    em.add_argument("--receiver", required=True)
    em.add_argument("--type", required=True, dest="msg_type")
    em.add_argument("--payload", default="{}")
    ls = sub.add_parser("listen")
    ls.add_argument("--agent", required=True)
    sub.add_parser("health")
    args = parser.parse_args()

    if args.action == "emit":
        payload = json.loads(args.payload) if args.payload else {}
        bus.emit(args.sender, args.receiver, args.msg_type, payload)
    elif args.action == "listen":
        msgs = bus.last(args.agent)
        print(json.dumps(msgs, indent=2, ensure_ascii=False))
    elif args.action == "health":
        exists = BUS_FILE.exists()
        print(json.dumps({"bus": "ok" if exists else "empty", "path": str(BUS_FILE)}))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
