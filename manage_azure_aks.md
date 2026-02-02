# 🎓 The Ultimate Master Guide to Azure AKS
> **Project**: IEEE-CIS Fraud Detection Deployment
> **Version**: 2.0 (Expert Edition)

This guide provides every command you need to manage, scale, and fix your AKS infrastructure like a pro.

---

## 🏗️ 0. Azure CLI Mastery (Infrastructure)
Control the "Hardware" level of your cluster.

### Connect & Auth
```bash
# Update local config to track the cluster
az aks get-credentials --resource-group fraud-detection-rg --name fraud-aks-cluster --overwrite-existing

# List available clusters in your subscription
az aks list -o table

# Link AKS to your Container Registry (ACR) if images aren't pulling
az aks update -n fraud-aks-cluster -g fraud-detection-rg --attach-acr mlopsfraud
```

### Power Controls (Save $$$)
```bash
# Stop the VMs (Best for weekends/sleep)
az aks stop --name fraud-aks-cluster --resource-group fraud-detection-rg

# Start them back up
az aks start --name fraud-aks-cluster --resource-group fraud-detection-rg
```

### Scale the "Servers" (Nodes)
```bash
# Manually add more VMs to the pool
az aks scale --resource-group fraud-detection-rg --cluster-name fraud-aks-cluster --node-count 3
```

---

## 🔍 1. Advanced Inspection (The "Eyes")
Go beyond simple `get pods`.

### Enhanced List
```bash
# See IPs and Nodes where pods are running
kubectl get pods -o wide

# Show pod labels (Useful for targeting)
kubectl get pods --show-labels

# List EVERYTHING in your namespace (Services, Deployments, ReplicaSets, Jobs)
kubectl get all
```

### Live Tracking
```bash
# Watch pods update in real-time
watch -n 1 kubectl get pods

# List all Events (The "Newsfeed" of your cluster)
kubectl get events --sort-by='.lastTimestamp'
```

---

## 🛠️ 2. Inside the Machine (The "Hands")
Need to touch the code or move files?

### Shell Into the Container
```bash
# Open a bash/sh session inside a running pod
kubectl exec -it inference-service-xxxx -- /bin/bash

# Run a one-off command without entering
kubectl exec inference-service-xxxx -- ls /app/models
```

### Transfer Files
```bash
# Copy a file from your Laptop -> Cloud Pod
kubectl cp tests/sample_data.csv inference-service-xxxx:/app/data.csv

# Download a file from Cloud Pod -> Laptop
kubectl cp inference-service-xxxx:/app/logs/app.log ./local_debug.log
```

---

## 📈 3. Performance & Scaling (The "Health")
Monitor CPU, RAM, and Auto-scaling.

### Resource Usage
```bash
# Which pods are eating the most CPU/RAM?
kubectl top pods

# Which node is under heavy load?
kubectl top nodes
```

### HPA (Autoscaling)
```bash
# Check the status of your horizontal pod autoscaler
kubectl get hpa

# Watch HPA scale your pods live during a stress test
kubectl get hpa -w
```

---

## 🚨 4. Advanced Debugging (The "Brain")
When things go wrong.

### The "Explain" Command
```bash
# See detailed status and event history (CRITICAL for Pending/Errors)
kubectl describe pod inference-service-xxxx

# Describe a specific service to check LoadBalancer status
kubectl describe svc inference-service
```

### Logs Mastery
```bash
# Stream logs from multiple pods at once (matching a label)
kubectl logs -l app=inference -f --tail=50

# See logs of a pod that already crashed (Previously)
kubectl logs inference-service-xxxx --previous
```

---

## ⚡ 5. Productivity Hacks (The "Speed")

### Aliases (Type less!)
Add these to your `~/.bashrc` or `~/.zshrc`:
```bash
alias k='kubectl'
alias kgp='kubectl get pods'
alias kgs='kubectl get svc'
alias kdl='kubectl delete pod'
alias klogs='kubectl logs -f'
```

### JSON Path (Filter precisely)
```bash
# Get only the External IP of the LoadBalancer
kubectl get svc inference-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

---

## 🌋 6. Common Error Troubleshooting
| Status | Meaning | Fix |
| :--- | :--- | :--- |
| `ImagePullBackOff` | Wrong name/path or No Auth | `az aks update --attach-acr ...` |
| `Pending` | No space left on Nodes | Scale up nodes with `az aks scale` |
| `CrashLoopBackOff` | Application code is crashing | Check `kubectl logs --previous` |
| `OOMKilled` | Pod used too much RAM | Increase `limits.memory` in `inference.yaml` |

---

## 🌍 7. Networking & Port Forwarding
```bash
# SECURE TUNNEL: Access the private API as if it were local
kubectl port-forward svc/inference-service 8080:8000

# Now you can hit http://localhost:8080 without exposing to the internet!
```

---
**Tip**: Use `kubectl get pods --all-namespaces` if you accidentally deploy to the wrong place! 🚀
