# Running Service Registry on Kubernetes/Minikube

This guide shows how to deploy the Service Registry on Kubernetes using Minikube.

## 📋 Prerequisites

1. **Install Minikube**: https://minikube.sigs.k8s.io/docs/start/
2. **Install kubectl**: https://kubernetes.io/docs/tasks/tools/
3. **Docker** (for building images)

## 🚀 Quick Start

### Step 1: Start Minikube

```bash
# Start Minikube
minikube start

# Enable metrics (optional)
minikube addons enable metrics-server

# Verify it's running
kubectl get nodes
```

### Step 2: Build Docker Image

```bash
# Point Docker to Minikube's Docker daemon
eval $(minikube docker-env)

# Build the image
docker build -t service-registry:latest .

# Verify the image
docker images | grep service-registry
```

### Step 3: Deploy the Service Registry

```bash
# Deploy the registry
kubectl apply -f k8s/registry-deployment.yaml

# Check deployment status
kubectl get deployments
kubectl get pods
kubectl get services

# Wait for pod to be ready
kubectl wait --for=condition=ready pod -l app=service-registry --timeout=60s
```

### Step 4: Access the Registry

```bash
# Get Minikube IP
minikube ip

# Access the registry (replace <MINIKUBE_IP> with actual IP)
curl http://<MINIKUBE_IP>:30001/health

# Or use port forwarding
kubectl port-forward service/service-registry 5001:5001

# Then access at localhost
curl http://localhost:5001/health
```

### Step 5: Deploy Example Services (User & Payment)

```bash
# Deploy user-service and payment-service
kubectl apply -f k8s/example-service-deployment.yaml

# Check all pods
kubectl get pods

# You should see:
# - service-registry-xxx (1 pod)
# - user-service-xxx (2 pods)
# - payment-service-xxx (1 pod)
```

### Step 6: Deploy Key-Value Service (kv-service)

```bash
# Deploy kv-service (2 replicas, ClusterIP service)
kubectl apply -f k8s/kv-service-deployment.yaml

# Check pods and services
kubectl get pods
kubectl get svc
```

You should now see:

- `service-registry-xxx` (1 pod)
- `user-service-xxx` (2 pods)
- `payment-service-xxx` (1 pod)
- `kv-service-xxx` (2 pods)

### Step 7: Test Service Discovery (including kv-service)

```bash
# Port forward the registry
kubectl port-forward service/service-registry 5001:5001

# In another terminal, test the API
curl http://localhost:5001/services

# Discover user-service
curl http://localhost:5001/discover/user-service

# You should see 2 instances of user-service!

# Discover kv-service
curl http://localhost:5001/discover/kv-service

# You should see 2 instances of kv-service!

# Run the Python demo client (from your machine, not inside the cluster)
python kv_client_demo.py  # uses http://localhost:5001 by default

# The script will:
# - Check registry health
# - Discover kv-service
# - Randomly choose one instance
# - Perform PUT/GET/DELETE on /kv/demo-key against the chosen instance
```

## 🔍 Monitoring and Debugging

### View Logs

```bash
# Registry logs
kubectl logs -l app=service-registry -f

# User service logs
kubectl logs -l app=user-service -f

# Specific pod logs
kubectl logs <pod-name>
```

### Check Pod Status

```bash
# Get all pods with details
kubectl get pods -o wide

# Describe a pod
kubectl describe pod <pod-name>

# Get pod events
kubectl get events --sort-by=.metadata.creationTimestamp
```

### Execute Commands in Pods

```bash
# Get a shell in the registry pod
kubectl exec -it <registry-pod-name> -- /bin/bash

# Test from inside the pod
kubectl exec -it <registry-pod-name> -- curl http://localhost:5001/health
```

## 📊 Architecture in Kubernetes

```
┌─────────────────────────────────────────────────────────┐
│                    Minikube Cluster                      │
│                                                           │
│  ┌────────────────────────────────────────────────┐    │
│  │         Service Registry (NodePort 30001)       │    │
│  │                                                  │    │
│  │  Pod: service-registry-xxx                      │    │
│  │  Container: registry (port 5001)                │    │
│  └────────────────────────────────────────────────┘    │
│                          ▲                               │
│                          │                               │
│         ┌────────────────┼────────────────┐            │
│         │                │                │            │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐   │
│  │ user-service│  │ user-service│  │   payment-  │   │
│  │   Pod 1     │  │   Pod 2     │  │   service   │   │
│  │             │  │             │  │   Pod 1     │   │
│  └─────────────┘  └─────────────┘  └────────────┘   │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

## 🎯 Key Kubernetes Concepts Demonstrated

### 1. Deployments
- **service-registry**: 1 replica (single registry instance)
- **user-service**: 2 replicas (demonstrates multiple instances)
- **payment-service**: 1 replica

### 2. Services
- **NodePort**: Exposes registry externally (port 30001)
- **ClusterIP**: Internal services for user-service and payment-service

### 3. Health Probes
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 5001
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 5001
  initialDelaySeconds: 5
  periodSeconds: 5
```

### 4. Environment Variables
```yaml
env:
- name: POD_IP
  valueFrom:
    fieldRef:
      fieldPath: status.podIP
```

## 🧪 Testing Scenarios

### Scenario 1: Service Registration

```bash
# Watch registry logs
kubectl logs -l app=service-registry -f

# In another terminal, watch services register
curl http://localhost:5001/services
```

### Scenario 2: Pod Scaling

```bash
# Scale user-service to 3 replicas
kubectl scale deployment user-service --replicas=3

# Watch new instances register
curl http://localhost:5001/discover/user-service

# Scale down to 1
kubectl scale deployment user-service --replicas=1

# Watch instances deregister (after 30s timeout)
```

### Scenario 3: Pod Failure

```bash
# Delete a pod
kubectl delete pod <user-service-pod-name>

# Kubernetes will create a new one
kubectl get pods -w

# New pod will register automatically
curl http://localhost:5001/discover/user-service
```

### Scenario 4: Rolling Update

```bash
# Update the image (after making changes)
eval $(minikube docker-env)
docker build -t service-registry:v2 .

# Update deployment
kubectl set image deployment/user-service user-service=service-registry:v2

# Watch rolling update
kubectl rollout status deployment/user-service
```

## 🔧 Troubleshooting

### Issue: Pods not starting

```bash
# Check pod status
kubectl describe pod <pod-name>

# Common issues:
# - Image not found: Make sure you built with minikube's Docker
# - CrashLoopBackOff: Check logs with kubectl logs
```

### Issue: Can't access registry

```bash
# Check service
kubectl get svc service-registry

# Check if port-forward is running
kubectl port-forward service/service-registry 5001:5001

# Test from within cluster
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -- \
  curl http://service-registry:5001/health
```

### Issue: Services not registering

```bash
# Check if registry is accessible from pods
kubectl exec -it <user-service-pod> -- \
  curl http://service-registry:5001/health

# Check environment variables
kubectl exec <user-service-pod> -- env | grep POD_IP
```

## 🧹 Cleanup

```bash
# Delete all resources
kubectl delete -f k8s/example-service-deployment.yaml
kubectl delete -f k8s/registry-deployment.yaml

# Or delete everything in the namespace
kubectl delete all --all

# Stop Minikube
minikube stop

# Delete Minikube cluster
minikube delete
```

## 📈 Advanced Topics

### 1. Persistent Storage

For production, you'd want to persist the registry data:

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: registry-storage
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 1Gi
```

### 2. ConfigMaps for Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: registry-config
data:
  HEARTBEAT_TIMEOUT: "30"
  CLEANUP_INTERVAL: "10"
```

### 3. Horizontal Pod Autoscaling

```bash
# Enable autoscaling based on CPU
kubectl autoscale deployment user-service \
  --cpu-percent=50 \
  --min=2 \
  --max=10
```

### 4. Ingress for External Access

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: registry-ingress
spec:
  rules:
  - host: registry.local
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: service-registry
            port:
              number: 5001
```

## 🎓 Learning Resources

- **Kubernetes Basics**: https://kubernetes.io/docs/tutorials/kubernetes-basics/
- **Minikube Tutorial**: https://minikube.sigs.k8s.io/docs/tutorials/
- **Service Discovery in K8s**: https://kubernetes.io/docs/concepts/services-networking/service/

## 🔄 Comparison: Local vs Kubernetes

| Feature | Local (venv) | Kubernetes |
|---------|-------------|------------|
| Deployment | Manual | Automated |
| Scaling | Manual | Automatic |
| Health Checks | Manual | Built-in |
| Load Balancing | None | Automatic |
| Self-Healing | None | Automatic |
| Service Discovery | Custom | Built-in DNS |
| Monitoring | Manual | Integrated |

## 🎯 Next Steps

1. **Try the deployment** following the Quick Start
2. **Experiment with scaling** - add/remove replicas
3. **Test failure scenarios** - delete pods and watch recovery
4. **Add monitoring** - integrate Prometheus/Grafana
5. **Implement persistence** - add database backend
6. **Set up CI/CD** - automate deployments

Happy Kubernetes learning! 🚀