# 🎓 The Ultimate Guide to Managing Azure AKS
> **For**: IEEE-CIS Fraud Detection Project
> **Goal**: Master your Kubernetes Cluster from the local terminal.

---

## 🔌 1. Connection (The "Key")
Before you can do anything, you must connect your local terminal to the cloud cluster.

**Command to Connect:**
```bash
az aks get-credentials --resource-group fraud-detection-rg --name fraud-aks-cluster --overwrite-existing
```
*   **What it does**: Downloads a "Key file" (kubeconfig) so your `kubectl` command knows how to talk to Azure.
*   **When to run**: Only once (or if you switch computers).

---

## 🔍 2. Inspection (The "Eyes")
Use these commands to see what is happening inside.

### Check the Nodes (Servers)
```bash
kubectl get nodes
```
*   **Expected**: You should see 2 lines (your VM workers) with status `Ready`.

### Check the Pods (Containers)
```bash
kubectl get pods
```
*   **Expected**: You should see `inference-service-xxxx` running.
*   **Watch Mode**: `kubectl get pods -w` (Updates live!)

### Check the Services (Load Balancers)
```bash
kubectl get services
```
*   **Why**: Look for the **EXTERNAL-IP** column for `inference-service`.
*   **Action**: Copy that IP (e.g., `20.55.11.22`) and paste it in your browser/Postman.

---

## 🛠️ 3. Debugging (The "Fix")
Something crashed? Or getting a 500 error? Use these.

### View Logs (Print Statements)
See exactly what Python is printing (errors, accessing S3, etc).
```bash
# 1. Get the full name first
kubectl get pods

# 2. View logs
kubectl logs inference-service-5d6f8-abcde
```
*   **Real-time logs**: `kubectl logs -f inference-service-xxxx` (Stream logs like tail -f)

### Describe Pod (Deep Dive)
If a pod is stuck in `Pending` or `CrashLoopBackOff`, this tells you **why**.
```bash
kubectl describe pod inference-service-xxxx
```
*   **Look for**: Valid events at the bottom (e.g., "Insufficient CPU", "Failed to pull image").

---

## 🕹️ 4. Manual Actions (The "Controls")

### Run the Manual Training Job
Since we disabled the auto-schedule (Feb 31st), here is how you trigger training manually.
```bash
kubectl create job --from=cronjob/training-job manual-training-run-001
```
*   *Note*: Change the name (`001`, `002`) each time you run it.

### Scale Up Manually
Want 10 pods right now?
```bash
kubectl scale deployment inference-service --replicas=10
```
*(Note: HPA might fight you and try to scale it back down after a minute!)*

### Restart Everything
If code looks weird or stuck, force a restart (pulls fresh images).
```bash
kubectl rollout restart deployment/inference-service
```

---

## 🏠 5. Local Testing (The "Port Forward")
Want to test the cloud API right here on your laptop without using the public IP?

```bash
kubectl port-forward svc/inference-service 8000:8000
```
*   **Now open**: `http://localhost:8000/docs` in your browser.
*   **Magic**: It tunnels traffic from your laptop -> Azure Cloud -> Pod securely.

---

## 🧹 6. Cleanup (Save Money!)
Pause the cluster when you sleep so you don't pay for the VMs.

**Stop Cluster (Pause Billing for Compute)**
```bash
az aks stop --name fraud-aks-cluster --resource-group fraud-detection-rg
```

**Start Cluster (Resume)**
```bash
az aks start --name fraud-aks-cluster --resource-group fraud-detection-rg
```
