# 🚀 Ultimate Guide to Managing Azure AKS & ACR
This guide covers everything you need to connect, control, scale, and troubleshoot your production-grade Kubernetes cluster and Container Registry.

---

## 🔑 1. Connection & Setup
*Get access to your cloud resources from your local terminal.*

### Login to Azure
```bash
az login
```

### Connect to AKS Cluster (Get `kubectl` access)
*Run this if `kubectl` says "no such host" or connection refused.*
```bash
# Variables: RG=fraud-detection-rg, CLUSTER=fraud-aks-cluster
az aks get-credentials --resource-group fraud-detection-rg --name fraud-aks-cluster --overwrite-existing
```

### Verify Connection
```bash
kubectl get nodes
```

---

## 🛠 2. Workload Management (The Basics)
*Manage your running containers (Pods) and Services.*

### Check Status
```bash
# Watch pods in real-time
kubectl get pods -w

# See all resources (Deployments, Services, HPA)
kubectl get all
```

### Inspecting Issues
```bash
# View logs of a specific pod
kubectl logs <pod-name>

# View logs of the previous crashed instance
kubectl logs <pod-name> --previous

# Describe a pod (Why is it pending/crashing?)
kubectl describe pod <pod-name>
```

### Accessing a Running Container (Smart Debugging)
```bash
# Open a shell inside the container
kubectl exec -it <pod-name> -- /bin/bash
```

---

## 🌐 3. Networking & Public Access
*Handling "lots of publics" (Traffic Management).*

### Get Public IP
```bash
kubectl get svc
# Look under 'EXTERNAL-IP' for 'inference-service'
```

### Check Load Balancer Status
```bash
kubectl describe svc inference-service
```
*Note: If EXTERNAL-IP is `<pending>` for too long, check `kubectl describe svc` for Azure quota or permission errors.*

### Test Endpoint
```bash
curl -X 'POST' 'http://<EXTERNAL-IP>/predict' \
  -H 'Content-Type: application/json' \
  -d '{"transactions": [{"TransactionID": 1001, "TransactionAmt": 50.0}]}'
```

---

## 📈 4. Smart Scaling (Handling High Traffic)
*Scale your application to handle thousands of requests.*

### Horizontal Pod Autoscaler (HPA)
*Automatically adds more Pods when CPU/Memory usage is high.*

```bash
# Check current HPA status
kubectl get hpa

# Watch HPA in real-time
kubectl get hpa -w
```
*(Your HPA is configured to scale between **2** and **8** pods based on CPU usage).*

### Scaling Nodes (Cluster Autoscaler)
*If you run out of Pods capacity, scale the VM nodes.*

```bash
# Manually scale node count (e.g., to 3 items)
az aks scale --resource-group fraud-detection-rg --name fraud-aks-cluster --node-count 3
```

---

## � 5. GPU Acceleration (T4)
*Power up your training jobs with NVIDIA T4 GPUs.*

### Add GPU Node Pool
*Add a new pool of VM nodes dedicated to GPU workloads (e.g., NCasT4_v3).*
```bash
# Variables: RG=fraud-detection-rg, CLUSTER=fraud-aks-cluster
az aks nodepool add \
    --resource-group fraud-detection-rg \
    --cluster-name fraud-aks-cluster \
    --name gpunodes \
    --node-count 1 \
    --node-vm-size Standard_NC4as_T4_v3 \
    --mode User
```

### Verify GPU Nodes
```bash
kubectl get nodes -l agentpool=gpunodes
```
*(Drivers are pre-installed via the NVIDIA device plugin).*

### Usage in Deployment (YAML)
*Request GPU resources in your pod spec.*
```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

### 💰 Cost Saver: Spot Instances
*Use Spot instances for training jobs to save ~90%.*
```bash
az aks nodepool add \
    --resource-group fraud-detection-rg \
    --cluster-name fraud-aks-cluster \
    --name gpuspot \
    --priority Spot \
    --eviction-policy Delete \
    --spot-max-price -1 \
    --enable-cluster-autoscaler \
    --min-count 1 --max-count 3 \
    --node-vm-size Standard_NC4as_T4_v3
```

---

## �🔄 6. Updates & Rollouts
*Deploy new code without downtime.*

### Rolling Restart
*Force pods to restart and pick up the latest config/secrets.*
```bash
kubectl rollout restart deployment/inference-service
```

### Apply Configuration Changes (YAML Updates)
*Use this when you modify a YAML file (e.g., adding environment variables, changing ports, or updating labels for monitoring).*
```bash
# Apply changes from a specific file
kubectl apply -f kubernetes/aks/inference.yaml
```
**Why use this?**
- **Updates Live State**: Syncs your running cluster resources with your local configuration files.
- **Enables Monitoring**: Crucial when you add metadata (like `app: inference` labels or named ports) that tools like Prometheus need to discover your service.


### Manual Image Update
*If you pushed a new image to ACR manually and want K8s to use it immediately.*
```bash
# Format: <acr-name>.azurecr.io/repo:tag
kubectl set image deployment/inference-service inference-container=mlopsfraud.azurecr.io/fraud-inference:latest
```

### Check Rollout Status
```bash
kubectl rollout status deployment/inference-service
```

### Undo a Bad Deployment
```bash
kubectl rollout undo deployment/inference-service
```

---

## 💸 7. Cost Management (Smart Control)
*Don't pay for what you don't use.*

### Stop Cluster (Nights/Weekends)
*Pauses the Control Plane and Nodes. You won't be charged for compute, only storage.*
```bash
az aks start --resource-group fraud-detection-rg --name fraud-aks-cluster
az aks stop --resource-group fraud-detection-rg --name fraud-aks-cluster
```
**CRITICAL:** When you start the cluster again, the Public IP might change (unless you configured a Static IP). Always run `kubectl get svc` after starting.

---

## 📦 8. ACR Management (Docker Images)
*Manage your stored Docker images.*

### Login to ACR
```bash
az acr login --name mlopsfraud
```

### List All Repositories
```bash
az acr repository list --name mlopsfraud --output table
```

### Show Tags (Versions) for a Repo
```bash
# For inference
az acr repository show-tags --name mlopsfraud --repository fraud-inference --output table

# For training
az acr repository show-tags --name mlopsfraud --repository fraud-training --output table
```

### Clean Up Old Images (Save Storage Costs)
*Delete a specific tag*
```bash
az acr repository delete --name mlopsfraud --image fraud-inference:old-tag-sha --yes
```

---

## ⚡ 9. Pro Tips (Cheat Sheet)
- **Alias**: Add `alias k=kubectl` to your bash profile to type less.
- **Dry Run**: Validate a yaml file without applying it:
  `kubectl apply -f file.yaml --dry-run=client`
- **Port Forward**: Test a service locally without exposing it to the internet:
  `kubectl port-forward svc/inference-service 8000:80`
  *(Then access localhost:8000)*




---

## 🚀 10. Manually Trigger Training Job
*Run the training pipeline on-demand anywhere (even if scheduled).*

```bash
# Create a one-off job from the CronJob template
kubectl create job --from=cronjob/training-job manual-training-001
```

*To check progress:*
```bash
kubectl get pods
kubectl logs manual-training-001-xxxxx -f
```

---

## 🔄 11. Full Redeployment Workflow (Code Update)
*Follow these steps when you change code (e.g., adding metrics) and need to update the running service.*

### Step 1: Login to ACR
```bash
az acr login --name mlopsfraud
```

### Step 2: Build & Push New Image
*Rebuild the Docker image with your latest changes.*
```bash
# Build (replace 'latest' with a version tag for production)
docker build -f docker/inference.Dockerfile -t mlopsfraud.azurecr.io/fraud-inference:latest .

# Push to Azure Container Registry
docker push mlopsfraud.azurecr.io/fraud-inference:latest
```

### Step 3: Update Cluster
*Apply the YAML configuration to restart pods with the new image.*
```bash
# This updates the Deployment spec and triggers a rolling restart
kubectl apply -f kubernetes/aks/inference.yaml
```
*Note: If you used `latest` tag and `imagePullPolicy: Always` is set, pods will pull the new image on restart.*