## Key-Value Microservice Discovery Demo

This guide shows how to run the **kv-service** microservice with **two instances**, register them with the existing registry in Minikube, and use the **kv_client_demo.py** client to discover and call a **random instance**.

### Prerequisites

- Minikube installed and running
- kubectl installed and configured to talk to your Minikube cluster
- Docker installed

All commands below are run from the repository root.

### 1. Start Minikube

```bash
minikube start
minikube addons enable metrics-server   # optional
kubectl get nodes
```

### 2. Build the Docker image inside Minikube

```bash
# Point Docker to Minikube's Docker daemon
eval $(minikube docker-env)

# Build the image (includes registry, kv-service, and client demo)
docker build -t service-registry:latest .

# Verify
docker images | grep service-registry
```

### 3. Deploy the service registry

```bash
kubectl apply -f k8s/registry-deployment.yaml

kubectl get deployments
kubectl get pods
kubectl get svc

kubectl wait --for=condition=ready pod -l app=service-registry --timeout=60s
```

### 4. Deploy the key-value service (kv-service)

```bash
kubectl apply -f k8s/kv-service-deployment.yaml

kubectl get pods
kubectl get svc
```

You should see two `kv-service` pods and a `kv-service` ClusterIP service on port 8001.

### 5. Inspect registered services

Port-forward the registry so you can query it from your machine:

```bash
kubectl port-forward service/service-registry 5001:5001
```

In a new terminal:

```bash
curl http://localhost:5001/health
curl http://localhost:5001/services
curl http://localhost:5001/discover/kv-service
```

You should see at least two instances listed under `kv-service`.

### 6. Run the client demo (random instance selection)

The registry returns pod-internal IPs (e.g., `10.244.x.x`) that are only reachable from inside the Minikube cluster. The client therefore needs to run inside the cluster too.

Launch the client as a one-off pod:

```bash
kubectl run kv-client --rm -it --restart=Never \
  --image=service-registry:latest \
  --image-pull-policy=Never \
  -- python kv_client_demo.py http://service-registry:5001
```

What the script does:

- Checks the registry health
- Calls `GET /discover/kv-service` to retrieve the list of active instances
- Picks a **random instance** from the `instances` array
- Performs a `PUT` → `GET` → `DELETE` cycle on `/kv/demo-key` against the chosen instance
- Prints every request and response for visibility

Run the command multiple times to see it occasionally choose different instances.

### 7. Clean up

```bash
kubectl delete -f k8s/kv-service-deployment.yaml
kubectl delete -f k8s/registry-deployment.yaml

minikube stop
```

