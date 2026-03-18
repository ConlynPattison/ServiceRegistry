import random
import sys
from typing import Any, Dict, List

import requests


def get_registry_url() -> str:
    if len(sys.argv) > 1:
        return sys.argv[1]
    return "http://localhost:5001"


def check_registry_health(registry_url: str) -> None:
    resp = requests.get(f"{registry_url}/health", timeout=5)
    resp.raise_for_status()


def discover_kv_service(registry_url: str) -> List[Dict[str, Any]]:
    resp = requests.get(f"{registry_url}/discover/kv-service", timeout=5)
    if resp.status_code != 200:
        raise RuntimeError(f"Discovery failed: {resp.status_code} {resp.text}")
    data = resp.json()
    instances = data.get("instances", [])
    if not instances:
        raise RuntimeError("No kv-service instances discovered")
    return instances


def put_get_delete_cycle(instance_address: str, key: str) -> None:
    base = instance_address.rstrip("/")
    value = {"demo": "value", "instance": instance_address}

    print(f"  PUT  /kv/{key} -> {base}")
    put_resp = requests.put(f"{base}/kv/{key}", json={"value": value}, timeout=5)
    put_resp.raise_for_status()
    print(f"    {put_resp.status_code} {put_resp.json()}")

    print(f"  GET  /kv/{key} -> {base}")
    get_resp = requests.get(f"{base}/kv/{key}", timeout=5)
    get_resp.raise_for_status()
    print(f"    {get_resp.status_code} {get_resp.json()}")

    print(f"  DELETE /kv/{key} -> {base}")
    del_resp = requests.delete(f"{base}/kv/{key}", timeout=5)
    del_resp.raise_for_status()
    print(f"    {del_resp.status_code} {del_resp.json()}")


def main() -> None:
    registry_url = get_registry_url()
    print(f"Using registry at {registry_url}")

    check_registry_health(registry_url)
    print("Registry is healthy")

    instances = discover_kv_service(registry_url)
    print(f"Discovered {len(instances)} kv-service instance(s):")
    for instance in instances:
        print(f"  - {instance['address']}")

    chosen = random.choice(instances)
    address = chosen["address"]
    print(f"\nRandomly chose instance: {address}\n")

    put_get_delete_cycle(address, "demo-key")
    print("\nCompleted PUT/GET/DELETE cycle successfully")


if __name__ == "__main__":
    main()

