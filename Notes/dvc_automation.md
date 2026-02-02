# DVC Pipeline Automation & S3 Integration 🔄

This document explains how we automated our Machine Learning pipeline using **DVC (Data Version Control)** and connected it to **AWS S3** for remote storage. This setup serves as the backbone of our MLOps workflow.

---

## 1. Why DVC? (The Problem)
In traditional software development, we use Git to version code. But data science has a unique problem:
- **Git is bad at handling large files.** (You can't push a 1GB CSV to GitHub).
- **Pipelines are complex.** If you change one preprocessing step, you shouldn't need to manually re-run every subsequent script. You need a system that knows the *dependencies*.

**Solution:** DVC acts as a layer on top of Git.
- Git tracks the *code* (`.py` files) and small configs (`dvc.yaml`).
- DVC tracks the *data* (`artifacts/`) and *models* (`models/`) by storing them in S3 and keeping only lightweight "pointer" files (hashes) in Git.

---

## 2. Setting up S3 Remote Storage
We used an AWS S3 bucket on free tier to serve as our "Remote Cache".

### Step 2.1: Initialization
Inside our project, we initialized DVC (similar to `git init`):
```bash
dvc init
```

### Step 2.2: Connecting S3
We told DVC "Use this S3 bucket to store the heavy stuff":
```bash
# S3REMOTE is just a name we picked
dvc remote add S3REMOTE -d s3://mlops-capstone-project-final/artifacts/
```

### Step 2.3: Authentication
DVC needs permission to talk to AWS. We configured it using environment variables (Best practice vs hardcoding keys):
```bash
# Variables are loaded from .env or system environment
dvc remote modify s3remote access_key_id $AWS_ACCESS_KEY_ID
dvc remote modify s3remote secret_access_key $AWS_SECRET_ACCESS_KEY
```

---

## 3. Defining the Pipeline (`dvc.yaml`)
This is the heart of the automation. Instead of running scripts manually like `python script1.py` then `python script2.py`, we defined the relationships in `dvc.yaml`.

The file defines a **DAG (Directed Acyclic Graph)**.

### Structure of a Stage
Each stage has three key parts:
1. **cmd**: The command to run.
2. **deps**: Dependencies. If these file change, DVC knows this stage is "outdated".
3. **outs**: Outputs. What this stage produces.

### Example: Our Pipeline
```yaml
stages:
  # STAGE 1: INGESTION
  data_ingestion:
    cmd: python -m src.components.data_ingestion
    dep: 
      - src/components/data_ingestion.py   # Code dependency
    outs:
      - artifacts/data/raw/raw_data.csv    # Output file

  # STAGE 2: TRANSFORMATION (Depends on Stage 1 Output)
  data_transformation:
    cmd: python -m src.components.data_FE_transformation
    deps:
      - src/components/data_FE_transformation.py
      - artifacts/data/raw/raw_data.csv    # <-- DEPENDENCY on Stage 1 output!
    outs:
      - artifacts/data/transformed/Train_transformed.csv
```

**The Magic:** Because Stage 2 depends on `raw_data.csv`, DVC guarantees that if you run Stage 2, it will ensure Stage 1 is run first (if needed).

---

## 4. The Automation Workflow
With `dvc.yaml` in place, our workflow becomes incredibly simple.

### 4.1 Reproducing Results (`dvc repro`)
When we want to run the pipeline, we don't remember scripts. We just type:
```bash
dvc repro
```
DVC checks the hashes.
- If dependencies haven't changed: "Stage is up to date." (Skips execution -> Saves time!)
- If code/data changed: Reruns ONLY the affected stages and downstream stages.

### 4.2 Pushing to Remote (`dvc push`)
After running the pipeline locally:
```bash
dvc push
```
This uploads the new `artifacts/` and `models/` to our S3 bucket.

### 4.3 Collaboration (`git push`)
We commit `dvc.lock` (which lists the exact md5 hashes of the data we just generated) to GitHub.
```bash
git add dvc.lock dvc.yaml
git commit -m "Update pipeline"
git push
```
**Teammate's Experience:**
A teammate pulls the code (`git pull`). They see the updated `dvc.lock`. They run `dvc pull`, and DVC downloads the *exact* matching data from S3. No manual file sharing needed!

---

## 5. Metrics & Plots (Experiment Tracking)
DVC also creates `dvc.lock` reports for metrics. In our `model_training` stage, we defined:
```yaml
  metrics:
    - models/metrics.json:
        cache: false
  plots:
    - models/confusion_matrix.png:
        cache: false
```
This allows us to use `dvc metrics show` or `dvc plots show` in the terminal to compare experiments without leaving the CLI.
