## Key-Value Microservice with Discovery

```mermaid
flowchart LR
  subgraph minikubeCluster[MinikubeCluster]
    registry["ServiceRegistry\n(NodePort 30001)"]
    subgraph kvNamespace["KeyValue Service Deployments"]
      kvPod1["KVService Pod 1\n(kv-service, port 8001)"]
      kvPod2["KVService Pod 2\n(kv-service, port 8001)"]
    end
  end

  clientProcess["ClientProcess\n(kv_client_demo.py)"]

  clientProcess -->|"1. GET /discover/kv-service"| registry
  registry -->|"2. JSON instances[]"| clientProcess
  clientProcess -->|"3. Randomly choose instance"| clientProcess
  clientProcess -->|"4. PUT/GET/DELETE /kv/<key>"| kvPod1
  clientProcess -->|"4. PUT/GET/DELETE /kv/<key>"| kvPod2

  kvPod1 -->|"register, heartbeat"| registry
  kvPod2 -->|"register, heartbeat"| registry
```

### Narrative

- Two replicas of the key-value microservice (`kv-service`) run as pods in the Minikube cluster.
- On startup, each pod:
  - Determines its address using the Kubernetes-provided `POD_IP`.
  - Registers itself with the `service-registry` under the logical name `kv-service`.
  - Sends periodic heartbeats so the registry can track active instances.
- The `kv_client_demo.py` process:
  - Calls the registry’s `/discover/kv-service` endpoint to retrieve the list of active instances.
  - Chooses a random instance from the returned `instances` list.
  - Performs a simple `PUT` → `GET` → `DELETE` cycle on `/kv/<key>` against the chosen instance to demonstrate request routing via discovery.

