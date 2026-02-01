# Continuous Deployment (CD) Master Plan & Learning Guide

> **Objective**: Implement a robust Continuous Deployment (CD) pipeline for the IEEE-CIS Fraud Detection System.
> **Philosophy**: "Teaching by doing" - We will break down every concept into simple terms.

---

## 🎓 Part 1: Key Concepts (The "Why" and "What")

Before we write code, let's understand the building blocks in simple words.

### 1. What is CD (Continuous Deployment)?
Imagine you are writing a book.
*   **CI (Continuous Integration)** is like an editor who checks your spelling every time you finish a page.
*   **CD (Continuous Deployment)** is the publisher who automatically prints the book and ships it to bookstores the moment the editor approves it.
*   **In our case**: CD takes your code, wraps it in a box (Container), and puts it on a server (Kubernetes) so users can see it.

### 2. What is a Container Registry? (ACR / ECR / Docker Hub)
*   **The Concept**: Think of a "Container Image" like a frozen meal. It has everything needed to eat (food, sauce, instructions).
*   **The Registry**: This is the super-freezer where we store these frozen meals.
    *   **Docker Hub**: A public freezer (like a supermarket).
    *   **ACR (Azure Container Registry)**: A private freezer just for Azure users (faster, more secure for Azure).
    *   **ECR (Amazon Elastic Container Registry)**: A private freezer just for AWS users.

### 3. What is Kubernetes? (AKS / EKS)
*   **The Concept**: If a Container is a ship, Kubernetes is the Harbor Master. It decides where ships dock, how many ships are needed, and what to do if a ship sinks (it replaces it).
*   **AKS (Azure Kubernetes Service)**: Microsoft's managed Harbor Master.
*   **EKS (Amazon Elastic Kubernetes Service)**: Amazon's managed Harbor Master.

---

## 🚀 Path 1: Azure Implementation (AKS + ACR)

This is the preferred path for Azure environments. We will move from Docker Hub to **Azure Container Registry (ACR)**.

### Step 1: Create the "Freezer" (Azure ACR)
First, we need a place to store our images on Azure.

#### Option A: Using the Terminal (Fastest)
```bash
# 1. Create a Resource Group (a folder for all resources)
az group create --name fraud-detection-rg --location eastus

# 2. Create the Registry (ACR)
# Note: Name must be globally unique!
az acr create --resource-group fraud-detection-rg --name frauddetectionacr --sku Basic --admin-enabled true
```

#### Option B: Using the Azure Portal (GUI)
1.  Go to [portal.azure.com](https://portal.azure.com).
2.  **Search Bar**: Type "Container Registries" and click it.
3.  **Top Left**: Click **+ Create**.
4.  **Basics Tab Configuration**:
    *   **Registry Name**: Type reasonable name (e.g., `mlopsfraud`).
    *   **Location**: `East US` (Same as your Resource Group).
    *   **Pricing plan (SKU)**: **Select `Basic`** (Crucial! `Standard` costs ~$0.66/day, `Basic` is ~$0.16/day).
    *   **Domain name label scope**: Select **Tenant Reuse** (or "Unsecure" if Tenant Reuse isn't available). This keeps your URL simple (`name.azurecr.io`) without extra hash characters.
    *   **Availability Zones**: Leave unchecked.
5.  **Review + Create**: Click the blue button at the bottom, wait for validation, then click **Create**.

### Step 1.5: Tooling & ID Check (Before you proceed)
You asked: *"Do I need to install tools? How do I find my ID?"*

**1. Install the Azure CLI (The Tool)**
Yes, to run `az` commands, you need the Azure Command Line Interface (CLI).
*   **Linux**: `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`
*   **Windows**: Download the MSI installer from Microsoft's website.
*   **Mac**: `brew install azure-cli`
*   *Alternative*: Use the **Cloud Shell** (icon looking like `>_` next to the search bar in Azure Portal) which has it pre-installed.

**2. Find your Subscription ID**
You need this for the next command.
*   **Option A (Portal)**: 
    1. Search for "Subscriptions" in the top bar.
    2. Copy the "Subscription ID" column (it looks like `a1b2c3d4-0000-0000-0000-...`).
*   **Option B (Terminal)**:
    Run `az login` (opens a browser), then run:
    ```bash
    az account show --query id -o tsv
    ```
    *(Copy this output)*.

### Step 2: The "Handshake" (Auth Credentials)
GitHub needs permission to put things in your Azure freezer.

> **💡 Knowledge Drop: Why not create an "IAM User" like in AWS?**
> *   **In AWS**, you often create an "IAM User" for a script.
> *   **In Azure**, "Users" are strictly for *humans* (like you). If you use a real User, the robot might fail because of Multi-Factor Authentication (MFA).
> *   **The Azure Way**: We create a **Service Principal**. Think of this as a "Robot Identity" specifically designed for apps. It has a specific ID and Password (Secret) but no human profile.
> *   The command below (`az ad sp...`) creates this Robot and gives it the key to your Resource Group.

#### Option A: Using the Terminal (Recommended)
This is highly recommended because the GUI method involves 15+ steps of creating App Registrations, Secrets, and assigning IAM roles manually.
```bash
# Create a Service Principal (a robot account for GitHub)
az login   ; to authentic
az ad sp create-for-rbac \
  --name "github-actions-fraud" \
  --role contributor \
  --scopes /subscriptions/<YOUR_SUBSCRIPTION_ID>/resourceGroups/fraud-detection-rg \
  --sdk-auth

# Copy the output (JSON) and save it as a Secret in GitHub named: AZURE_CREDENTIALS
```

### Step 3: Update CI Pipeline (`.github/workflows/ci.yaml`)
*Current Status*: Pushes to Docker Hub.
*New Status*: Pushes to Azure ACR.

**Changes Explanation**:
1.  **Remove** `docker/login-action` for Docker Hub.
2.  **Add** `azure/login` to authenticate with Azure.
3.  **Add** `az acr login` to open the registry door.
4.  **Update Images**: Change `tags` to use the ACR address (e.g., `frauddetectionacr.azurecr.io/...`).

**New `ci.yaml` Snippet (Replace the `build-and-push` job):**

```yaml
  build-and-push:
    name: Build & Push to Azure ACR
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # 1. Login to Azure
      - name: 'Az CLI login'
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      # 2. Login to ACR specifically
      - name: 'ACR Login'
        run: az acr login --name frauddetectionacr

      - uses: docker/setup-buildx-action@v3

      # 3. Build & Push Training Image
      - name: 🐳 Build & Push Training Image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/training.Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          tags: frauddetectionacr.azurecr.io/fraud-training:${{ github.sha }}, frauddetectionacr.azurecr.io/fraud-training:latest

      # 4. Build & Push Inference Image
      - name: 🐳 Build & Push Inference Image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: ${{ github.event_name != 'pull_request' }}
          tags: frauddetectionacr.azurecr.io/fraud-inference:${{ github.sha }}, frauddetectionacr.azurecr.io/fraud-inference:latest
```

### Step 4: Create the Harbor (AKS)
Now we create the Kubernetes cluster and attach it to our registry.

#### Option A: Using the Terminal (Fastest)
```bash
# Create AKS + Attach ACR (Magic command!)
# --attach-acr allows AKS to pull images from ACR without extra passwords
# --node-vm-size Standard_D2s_v3 ensures we use a widely available machine type
az aks create \
  --resource-group fraud-detection-rg \
  --name fraud-aks-cluster \
  --node-count 2 \
  --node-vm-size Standard_D2s_v3 \
  --attach-acr mlopsfraud \
  --generate-ssh-keys
```

> **⚠️ Common Errors & Fixes:**
> 1.  **"MissingSubscriptionRegistration"**: Run `az provider register --namespace Microsoft.ContainerService` and wait 2 mins.
> 2.  **"Cluster already exists"**: If the command failed halfway, the cluster might exist but be broken. Fix the ACR link by running:
>     `az aks update --resource-group fraud-detection-rg --name fraud-aks-cluster --attach-acr mlopsfraud`

#### Option B: Using the Azure Portal (GUI)
1.  **Search Bar**: Type "Kubernetes services" and click it.
2.  **Top Left**: Click **+ Create** -> **Kubernetes cluster**.
3.  **Basics Tab**:
    *   **Resource Group**: Select `fraud-detection-rg`.
    *   **Cluster Preset Config**: Choose "Dev/Test" (Cheaper).
    *   **Kubernetes Cluster Name**: Type `fraud-aks-cluster`.
    *   **Node Count** (Change usually found under Node Pools): Set to `2`.
4.  **Integrations Tab** (Crucial Step!):
    *   Look for **Container Registry**.
    *   Select `frauddetectionacr` from the dropdown. *This performs the "link" so AKS can pull images.*
5.  **Review + Create**: Click it, wait for validation, then click **Create**.

### Step 4.5: The Kubernetes Manifests
We need to define *how* our apps run. Create these files in `kubernetes/aks/`.

**1. `inference.yaml` (Deployment + Service + HPA)**
*   **Worker Node**: Targeted via `nodeSelector`.
*   **Scaling**: Min 2, Max 5 (Auto-scales based on CPU).
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: inference-service
spec:
  replicas: 2                     # Min Replicas (Starting point)
  selector:
    matchLabels:
      app: inference
  template:
    metadata:
      labels:
        app: inference
    spec:
      containers:
      - name: inference
        image: IMAGE_PLACEHOLDER
        ports:
        - containerPort: 8000
        resources:                # Required for HPA
          requests:
            cpu: "250m"
            memory: "256Mi"
          limits:
            cpu: "500m"
            memory: "512Mi"
        env:
        - name: AWS_ACCESS_KEY_ID
          valueFrom: {secretKeyRef: {name: app-secrets, key: AWS_ACCESS_KEY_ID}}
        - name: AWS_SECRET_ACCESS_KEY
          valueFrom: {secretKeyRef: {name: app-secrets, key: AWS_SECRET_ACCESS_KEY}}
      nodeSelector:
        kubernetes.io/os: linux   # Run on Worker Nodes

---
apiVersion: v1
kind: Service
metadata:
  name: inference-service
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 8000
  selector:
    app: inference

---
# Horizontal Pod Autoscaler (Min=2, Max=8)
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: inference-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: inference-service
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
```

> **💡 Knowledge Drop: What does "averageUtilization: 60" mean?**
> This is the "Trigger" for adding new pods.
> *   **The Logic**: "Kubernetes, watch the CPU usage. If the average across all pods goes **above 60%** of what we requested, add more pods!"
> *   **Why not 100%?**: It is a "Safety Buffer".
>     *   If traffic spikes suddenly, 60% gives you time to spin up a new pod (takes ~30s) before the existing pods crash at 100% load.
>     *   **Example**: If you have 2 pods at 50% usage, and traffic doubles:
>         *   With target 100%: Pods hit 100% and might crash/lag before help arrives.
>         *   With target 60%: Pods hit 60% $\rightarrow$ Kubernetes immediately starts a 3rd pod. The 3rd pod is ready *before* the first two get overwhelmed.

**2. `training.yaml` (The Manual Job)**
*   **Schedule**: set to **Feb 31st** (Never happens automatically). You must trigger this yourself.
*   **Targeting**: Attempts to use System nodes.
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: training-job
spec:
  # Manual Run Strategy: Set schedule to an invalid date (Feb 31st)
  # This disables auto-runs.
  schedule: "0 0 31 2 *" 
  jobTemplate:
    spec:
      parallelism: 1    
      backoffLimit: 2   
      template:
        spec:
          containers:
          - name: training
            image: TRAINING_IMAGE_PLACEHOLDER
            env:
            - name: AWS_ACCESS_KEY_ID
              valueFrom: {secretKeyRef: {name: app-secrets, key: AWS_ACCESS_KEY_ID}}
            - name: AWS_SECRET_ACCESS_KEY
              valueFrom: {secretKeyRef: {name: app-secrets, key: AWS_SECRET_ACCESS_KEY}}
          restartPolicy: OnFailure
          affinity:
            nodeAffinity:
              preferredDuringSchedulingIgnoredDuringExecution:
              - weight: 1
                preference:
                  matchExpressions:
                  - key: agentpool
                    operator: In
                    values:
                    - system
```

> **🕹️ How to Run Manual Training**
> Since we disabled the schedule, you must trigger it manually.
>
> **Where to run?**: In YOUR local terminal (WSL/Linux).
> *   *Prerequisite*: You must have connected to the cluster first (seen in steps below).
>
> **The Command**:
> ```bash
> # This creates a one-time job named 'manual-run-1' from the template
> kubectl create job --from=cronjob/training-job manual-training-run-1
> ```
> *   **Check status**: `kubectl get pods` (You will see a pod named `manual-training-run-1-xxxxx`).
> *   **View Logs**: `kubectl logs manual-training-run-1-xxxxx`.

### Step 4.6: Managing AKS from Local Terminal (Cheatsheet)
Once the cluster is created, you need to "log in" to it from your terminal to run manual jobs or check logs.

**1. Connect (The "Login" Command)**
Run this **once** to set up your local `kubectl`.
```bash
az aks get-credentials --resource-group fraud-detection-rg --name fraud-aks-cluster
```

**2. Inspection Commands (What's running?)**
*   `kubectl get nodes` -> See if your 2 VMs are ready.
*   `kubectl get pods` -> See all running containers (Inference, Training).
*   `kubectl get services` -> See the External IP (LoadBalancer) of your API.
*   `kubectl get hpa` -> See the Auto-Scaler status (Current CPU vs Target).

**3. Debugging Commands (Something broke!)**
*   `kubectl logs <pod-name>` -> **The most important command**. Read the python output/errors.
    *   *Example*: `kubectl logs inference-service-5d6f8-abcde`
*   `kubectl describe pod <pod-name>` -> "Why is it crashing?" (Show events like "CrashLoopBackOff" or "OOM").

**4. Testing Locally (Port Forwarding)**
Want to test the API without exposing it to the world yet?
```bash
# Forwards your local port 8000 to the pod's port 8000
kubectl port-forward svc/inference-service 8000:8000
```
*(Then you can request `localhost:8000/predict` in Postman!)*

### Step 5: Continuous Deployment (CD) Workflow
Create a NEW file `.github/workflows/deploy-aks.yml` that runs manually or after CI.

**The Workflow Code (`.github/workflows/deploy-aks.yml`):**
```yaml
name: Deploy to Azure AKS

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Image Tag to deploy (e.g., sha-12345 or latest)'
        required: true
        default: 'latest'

env:
  ACR_NAME: mlopsfraud
  RG: fraud-detection-rg
  CLUSTER: fraud-aks-cluster
  TAG: ${{ github.event.inputs.image_tag }}

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      # 1. Login to Azure
      - name: Azure Login
        uses: azure/login@v1
        with:
          creds: ${{ secrets.AZURE_CREDENTIALS }}
      
      # 2. Connect to AKS
      - name: Set AKS Context
        uses: azure/aks-set-context@v3
        with:
          resource-group: ${{ env.RG }}
          cluster-name: ${{ env.CLUSTER }}

      # 3. Create/Update Secrets in AKS
      - name: Update App Secrets
        run: |
          kubectl create secret generic app-secrets \
            --from-literal=AWS_ACCESS_KEY_ID=${{ secrets.AWS_ACCESS_KEY_ID }} \
            --from-literal=AWS_SECRET_ACCESS_KEY=${{ secrets.AWS_SECRET_ACCESS_KEY }} \
            --dry-run=client -o yaml | kubectl apply -f -

      # 4. Deploy Inference Service
      - name: Deploy Inference
        run: |
          sed -i "s|IMAGE_PLACEHOLDER|${{ env.ACR_NAME }}.azurecr.io/fraud-inference:${{ env.TAG }}|g" kubernetes/aks/inference.yaml
          kubectl apply -f kubernetes/aks/inference.yaml
          kubectl rollout restart deployment/inference-service

      # 5. Deploy Training Job
      - name: Deploy Training Job
        run: |
          sed -i "s|TRAINING_IMAGE_PLACEHOLDER|${{ env.ACR_NAME }}.azurecr.io/fraud-training:${{ env.TAG }}|g" kubernetes/aks/training.yaml
          kubectl apply -f kubernetes/aks/training.yaml
```

> **⚖️ Scaling Guide: How to choose Min/Max Pods?**
>
> When configuring your `inference.yaml`, you need to set the `replicas`.
>
> **1. Minimum Replicas (`replicas`)**
> *   **Rule**: Always **≥ 2 for Production**.
> *   **Why?**: If you have 1 pod and it crashes (or the node updates), your site goes down (500 Error).
> *   **For Us**: Use `1` for saving money while learning, `2` if you want to simulate real production.
>
> **2. Maximum Capacity**
> *   **Rule**: Based on your Cluster RAM/CPU.
> *   **Math**: Your AKS cluster has 2 nodes (Total ~8GB RAM). If one pod uses 500MB, you *could* fit ~10. To be safe, limit to **4 or 5** so you don't crash the cluster.


---

## ☁️ Path 2: AWS Implementation (EKS + ECR)

This path uses the AWS ecosystem. We replace Docker Hub with **Amazon ECR**.

### Step 1: Create the "Freezer" (AWS ECR)
AWS requires explicit repository creation for each image.

#### Option A: Using the Terminal
```bash
# Create Repository for Inference
aws ecr create-repository --repository-name fraud-inference --region us-east-1

# Create Repository for Training
aws ecr create-repository --repository-name fraud-training --region us-east-1
```

#### Option B: Using the AWS Console (GUI)
1.  Go to [console.aws.amazon.com](https://console.aws.amazon.com).
2.  **Search Bar**: Type "ECR" and select **Elastic Container Registry**.
3.  **Button**: Click **Create repository** (orange button).
4.  **Settings**:
    *   **Visibility**: "Private".
    *   **Repository name**: Type `fraud-inference`.
5.  **Create**: Click **Create repository** at the bottom.
6.  **Repeat**: Do the same steps again, but name it `fraud-training`.

### Step 2: Update CI Pipeline (For AWS)
In `ci.yaml`, we use `configure-aws-credentials` and `amazon-ecr-login`.

**Key Differences from Azure**:
*   Instead of one big login, we configure AWS credentials.
*   We use a dynamic variable for the registry URL because AWS URLs are long (e.g., `123456789.dkr.ecr.us-east-1.amazonaws.com`).

**New `ci.yaml` Snippet (AWS Version):**
```yaml
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: us-east-1

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2
      
      - name: 🐳 Build & Push Inference
        uses: docker/build-push-action@v5
        with:
          context: .
          file: docker/inference.Dockerfile
          push: true
          # Use result of previous step
          tags: ${{ steps.login-ecr.outputs.registry }}/fraud-inference:${{ github.sha }}
```

### Step 3: Create the Harbor (EKS)

#### Option A: Using the Terminal (Recommended)
`eksctl` handles 100+ steps of complexity for you (VPC setup, Subnets, IAM Roles, Route Tables, etc.).
```bash
eksctl create cluster \
  --name fraud-eks-cluster \
  --region us-east-1 \
  --nodes 2
```

#### Option B: Using the AWS Console (GUI - Advanced)
*Warning: This is much harder than Azure's GUI because AWS doesn't auto-create the network (VPC) for you in the wizard.*
1.  **Search Bar**: Type "EKS" -> **Elastic Kubernetes Service**.
2.  **Add Cluster**: Click **Add cluster** -> **Create**.
3.  **Configure Cluster**:
    *   **Name**: `fraud-eks-cluster`.
    *   **Cluster Service Role**: You must *pre-create* an IAM Role with `AmazonEKSClusterPolicy`. If you don't have one, go to IAM -> Roles -> Create Role -> EKS - Cluster -> Create. Then come back and refresh.
4.  **Networking**:
    *   **VPC**: You must select an existing VPC. If you don't have one, you must go to **VPC Console** -> Create VPC.
5.  **Configure Node Group** (After cluster is created):
    *   **Important**: You have to manually add "Compute" (Nodes). Go to the "Compute" tab of your new cluster -> **Add Node Group**.
    *   **IAM Role**: You need *another* pre-created IAM Role with `AmazonEKSWorkerNodePolicy` and `AmazonEC2ContainerRegistryReadOnly`.
    *   **Instance Type**: Select `t3.medium`.
    *   **Scaling config**: Desired size `2`.

*Note: For AWS, stick to the terminal (`eksctl`) if you value your sanity!*

### Step 4: Connecting the Dots
Unlike Azure's simple `--attach-acr`, AWS EKS needs permission to pull from ECR.
*   **The Easy Way**: The node role created by `eksctl` often has read-only access by default.
*   **The Hard Way**: Create an IAM Policy for ECR Read-Only and attach it to the EKS Workers.

---

## 📝 Check Your Understanding: "The Life Cycle of code"

Let's trace what happens when you modify `main.py` and push:

**In Azure Mode:**
1.  **You**: Push code (`git push`).
2.  **GitHub CI**: tests the code.
3.  **GitHub CI**: Builds a Docker image.
4.  **GitHub CI**: Logs into Azure.
5.  **GitHub CI**: Pushes image to **ACR** (our private freezer).
6.  **GitHub CD**: Logs into **AKS**.
7.  **GitHub CD**: Tells AKS, "Hey, update the `inference` deployment to use image version `sha-123`".
8.  **AKS**: Pulls the image from **ACR** and restarts the pods.
9.  **User**: Sees the new changes instantly.

**In AWS Mode:**
1.  **You**: Push code.
2.  **GitHub CI**: tests/builds.
3.  **GitHub CI**: Logs into AWS.
4.  **GitHub CI**: Pushes image to **ECR**.
5.  **GitHub CD**: Logs into **EKS**.
6.  **GitHub CD**: Updates Kubernetes manifest with ECR image URL.
7.  **EKS**: Pulls from **ECR** and restarts pods.
