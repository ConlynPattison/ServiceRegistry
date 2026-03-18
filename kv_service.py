import os
import signal
import sys
import threading
import time
from typing import Any, Dict

from flask import Flask, jsonify, request
import requests


app = Flask(__name__)


store_lock = threading.Lock()
store: Dict[str, Any] = {}


SERVICE_NAME = "kv-service"
REGISTRY_URL = os.environ.get("REGISTRY_URL", "http://service-registry:5001")
SERVICE_PORT = int(os.environ.get("SERVICE_PORT", "8001"))


def get_service_address() -> str:
    pod_ip = os.environ.get("POD_IP", "localhost")
    return f"http://{pod_ip}:{SERVICE_PORT}"


def register_with_registry() -> bool:
    address = get_service_address()
    try:
        response = requests.post(
            f"{REGISTRY_URL}/register",
            json={"service": SERVICE_NAME, "address": address},
            timeout=5,
        )
        return response.status_code in (200, 201)
    except Exception:
        return False


def deregister_from_registry() -> None:
    address = get_service_address()
    try:
        requests.post(
            f"{REGISTRY_URL}/deregister",
            json={"service": SERVICE_NAME, "address": address},
            timeout=5,
        )
    except Exception:
        pass


def send_heartbeat() -> None:
    address = get_service_address()
    try:
        requests.post(
            f"{REGISTRY_URL}/heartbeat",
            json={"service": SERVICE_NAME, "address": address},
            timeout=5,
        )
    except Exception:
        pass


stop_event = threading.Event()


def heartbeat_loop(interval_seconds: int = 10) -> None:
    while not stop_event.is_set():
        send_heartbeat()
        stop_event.wait(interval_seconds)


@app.route("/kv/<key>", methods=["PUT"])
def put_key(key: str):
    if not request.is_json:
        return jsonify({"status": "error", "message": "Request body must be JSON"}), 400

    body = request.get_json(silent=True) or {}
    if "value" not in body:
        return jsonify({"status": "error", "message": "Missing 'value' field"}), 400

    value = body["value"]

    with store_lock:
        store[key] = value

    return jsonify({"status": "ok", "key": key, "value": value}), 200


@app.route("/kv/<key>", methods=["GET"])
def get_key(key: str):
    with store_lock:
        if key not in store:
            return (
                jsonify(
                    {
                        "status": "not_found",
                        "message": f"Key '{key}' not found",
                        "key": key,
                    }
                ),
                404,
            )
        value = store[key]

    return jsonify({"status": "ok", "key": key, "value": value}), 200


@app.route("/kv/<key>", methods=["DELETE"])
def delete_key(key: str):
    with store_lock:
        if key not in store:
            return (
                jsonify(
                    {
                        "status": "not_found",
                        "message": f"Key '{key}' not found",
                        "key": key,
                    }
                ),
                404,
            )
        del store[key]

    return jsonify({"status": "deleted", "key": key}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/stats", methods=["GET"])
def stats():
    with store_lock:
        count = len(store)
    return jsonify({"keys": count}), 200


def _setup_signal_handlers():
    def handle_signal(signum, frame):
        stop_event.set()
        deregister_from_registry()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)


def main():
    if not register_with_registry():
        # Best-effort registration; still start service so it can be debugged
        pass

    _setup_signal_handlers()

    heartbeat_thread = threading.Thread(
        target=heartbeat_loop, kwargs={"interval_seconds": 10}, daemon=True
    )
    heartbeat_thread.start()

    app.run(host="0.0.0.0", port=SERVICE_PORT)


if __name__ == "__main__":
    main()

