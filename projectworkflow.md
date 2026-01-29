---------------------- setting up project structure ------------

1. create a virtual environment named 'atlas' : conda create -n atlas python=3.10
2. Activate the atlas env : conda activate atlas
3. pip install cookiecutter : to build project structure, the have multiple templetes on github i guess
   so it just create files and build project struture.
4. "cookiecutter -c v1 https://github.com/drivendata/cookiecutter-data-science" : to copy the templete (skip aws things we will setup this manually)
5. cut all files from newly created and past on root folder
6. rename src.models to src.model becasue we already have model in root so its like just to make the mind clear.
7. git push origin main


---------------------- setup MLflow on dagshub-------------

8. Go to: https://dagshub.com/dashboard
9. Create > New Repo > Connect a repo > (Github) Connect > Select your repo > Connect
10. Copy experiment tracking url and code snippet. (Also try: Go To MLFlow UI)
11. pip install dagshub && pip install mlflow

12. Now tracking experiment with 3 models in a loop using MLfow and dagsub,  file: exp1.ipynb






-------------------------------- Building src components--------------------------

1. Logging ------------------> 
   
   1.Write logger module : ok so we need a logger module so that we can save the logs for important steps in the whole project. 
   so to make the module(will be able to import on different folders):

   2. ---> create logger foler inside the src directory, then create __init__.py and write the code in this file
   3.---> best practice dont run the logged() in the last in __init__.py instead run the module where you are exporting it



2. local packages ------------>
   
   --install packages listed in requirement.txt, also
   --add e .  in the same file so that it will also install the local packages
   --install: pip install -r requirement.txt     or       "pip install -e ." to install local package  


















==============================================================================================
                    DVC + S3 REMOTE STORAGE + GIT TRACKING TUTORIAL
==============================================================================================

This section explains how to:
1. Track your artifacts folder with DVC
2. Push large files to AWS S3 (instead of Git)
3. Properly integrate DVC with Git/GitHub

==============================================================================================


---------------------- UNDERSTANDING: How DVC + Git Work Together ----------------------

┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                         THE BIG PICTURE                                                  │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   YOUR LOCAL MACHINE                      REMOTE STORAGE                                 │
│   ─────────────────                       ──────────────                                 │
│                                                                                          │
│   ┌─────────────────┐                     ┌─────────────────┐                           │
│   │ artifacts/      │ ──── dvc push ────► │  AWS S3 Bucket  │                           │
│   │ (large files)   │ ◄─── dvc pull ───── │  (large files)  │                           │
│   └─────────────────┘                     └─────────────────┘                           │
│           │                                                                              │
│           │ DVC tracks hashes                                                            │
│           ▼                                                                              │
│   ┌─────────────────┐                     ┌─────────────────┐                           │
│   │ dvc.lock        │ ──── git push ────► │    GitHub       │                           │
│   │ .dvc     │ ◄─── git pull ───── │  (small files)  │                           │
│   │ dvc.yaml        │                     │                 │                           │
│   └─────────────────┘                     └─────────────────┘                           │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘


WHAT GETS TRACKED WHERE?
─────────────────────────

| Track with GIT (small files)           | Track with DVC (large files)              |
|----------------------------------------|-------------------------------------------|
| ✓ dvc.yaml (pipeline definition)       | ✓ artifacts/ folder (CSVs, models, etc.)  |
| ✓ dvc.lock (file hashes & versions)    | ✓ Any file > 100MB                        |
| ✓ .dvc/config (remote settings)        | ✓ Training data, processed data           |
| ✓ *.dvc files (pointers to large data) | ✓ Model weights, checkpoints              |
| ✓ .dvcignore                           |                                           |


KEY INSIGHT: 
─────────────
Git stores the "address" (hash/pointer) of your large files.
DVC stores the actual large files on remote storage (S3).
When someone clones your repo, they get the pointers from Git, 
then run `dvc pull` to download the actual files from S3.



---------------------- STEP 1: Install DVC with S3 Support ----------------------

# Install DVC with S3 dependencies
pip install dvc[s3]

# Verify installation
dvc --version

# If DVC was already initialized (you have .dvc folder), skip to Step 2
# Otherwise initialize DVC:
dvc init



---------------------- STEP 2: Add artifacts Folder to DVC Tracking ----------------------

# Navigate to your project root
cd /home/pluto/Desktop/IEEE-CIS-Fraud-detection

# Add the entire artifacts folder to DVC tracking
dvc add artifacts

# This creates two things:
# 1. artifacts.dvc       → A small text file (pointer) that Git will track
# 2. artifacts/.gitignore  → Tells Git to ignore the actual files inside artifacts/

# WHAT HAPPENS INTERNALLY:
# ─────────────────────────
# DVC calculates a unique hash (MD5) of all files in artifacts/
# This hash is stored in artifacts.dvc
# The actual files are moved to .dvc/cache (local cache)
# A symbolic link or copy is placed back in artifacts/



Since we already added artifact/raw/raw_data.py   and artifacts/transformed. .csv files as output for each staging, so dvc track thsese files and push to remote storage. 

DVC just monitor dependencies to detect change so that if we rerun pipeline then it will detect oooh this stage component get changed so we need to run it again.





data_ingestion:
  deps:                                    # ❌ NOT pushed to S3
    - src/components/data_ingestion.py     # Just monitored
    - src/utils/fetch_data.py              # Just monitored
    - config/config.yaml                   # Just monitored
  outs:                                    # ✅ PUSHED to S3
    - artifacts/data/raw/raw_data.csv      # Cached & pushed



---------------------- STEP 3: Configure AWS S3 as Remote Storage ----------------------

# Create an S3 bucket on AWS Console first, then:

# Add S3 as a DVC remote (S3 uri)   ; -d means default
dvc remote add S3REMOTE -d s3://mlops-capstone-project-final/artifacts/

# Example:
# dvc remote add -d myremote s3://ieee-fraud-detection-artifacts/dvc-store

# The -d flag sets this as the DEFAULT remote

# Verify the remote was added
dvc remote list
# Should show: myremote    s3://YOUR_BUCKET_NAME/dvc-store



---------------------- STEP 4: Configure AWS Credentials for DVC ----------------------

There are 3 ways to provide AWS credentials to DVC:


METHOD 1: Using AWS CLI (Recommended)
─────────────────────────────────────
# Install AWS CLI if not installed
pip install awscli

# Configure AWS credentials
aws configure

# It will prompt for:
# AWS Access Key ID: YOUR_ACCESS_KEY
# AWS Secret Access Key: YOUR_SECRET_KEY  
# Default region name: us-east-1 (or your region)
# Default output format: json

# Credentials are stored in ~/.aws/credentials
# DVC automatically uses these credentials


METHOD 2: Using Environment Variables  : im choosig this method
─────────────────────────────────────
#export in terminal:
export AWS_ACCESS_KEY_ID=your_access_key
export AWS_SECRET_ACCESS_KEY=your_secret_key
export AWS_DEFAULT_REGION=us-east-1


METHOD 3: Direct DVC Configuration (stores in .dvc/config)
──────────────────────────────────────────────────────────
# WARNING: This stores credentials in a file. Be careful with version control!
dvc remote modify myremote access_key_id YOUR_ACCESS_KEY
dvc remote modify myremote secret_access_key YOUR_SECRET_KEY
dvc remote modify myremote region us-east-1

# For security, use --local flag to store credentials locally (not in Git):
dvc remote modify --local myremote access_key_id YOUR_ACCESS_KEY
dvc remote modify --local myremote secret_access_key YOUR_SECRET_KEY

# --local stores in .dvc/config.local which should be in .gitignore



---------------------- STEP 5: Push Data to S3 ----------------------

# Push all DVC-tracked files to S3
dvc push

# This uploads:
# - All files from .dvc/cache to S3
# - Uses the hash as the filename in S3

# To push specific files only:   we are tracking using piepline dvc.yaml so not gonnna do this
dvc push artifacts.dvc

# Verify upload (optional - check S3 console or use AWS CLI):
aws s3 ls s3://YOUR_BUCKET_NAME/dvc-store/ --recursive



---------------------- STEP 6: Track DVC Files with Git ----------------------

Now you need to commit the DVC pointer files to Git.

# Add DVC-related files to Git staging
git add dvc.yaml              # Pipeline definition
git add dvc.lock              # Pipeline state (hashes of inputs/outputs)
git add artifacts.dvc         # Pointer to artifacts folder (created by dvc add)
git add .dvc/config           # Remote storage configuration
git add .dvc/.gitignore       # DVC's internal gitignore

# If you have other .dvc files:
git add *.dvc

# Commit the changes
git commit -m "Add DVC tracking for artifacts with S3 remote"

# Push to GitHub
git push origin main


OPTIONAL: Enable Auto-Staging
─────────────────────────────
# This automatically stages DVC files when you run dvc commands
dvc config core.autostage true

# After this, you don't need to manually run `git add dvc.lock` 
# DVC will do it automatically when you run dvc repro, dvc add, etc.



---------------------- STEP 7: Complete Workflow Example ----------------------

Here's the complete workflow when working on your project:


SCENARIO A: You made changes to your pipeline/data
───────────────────────────────────────────────────
# 1. Run your pipeline
dvc repro

# 2. DVC automatically updates dvc.lock with new hashes

# 3. Push updated data to S3
dvc push

# 4. Commit the updated tracking files to Git
git add dvc.lock
git commit -m "Update pipeline outputs"
git push origin main


SCENARIO B: Someone clones your repo and wants the data
───────────────────────────────────────────────────────
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/IEEE-CIS-Fraud-detection.git
cd IEEE-CIS-Fraud-detection

# 2. Install dependencies
pip install -r requirements.txt
pip install dvc[s3]

# 3. Configure AWS credentials (one of the methods from Step 4)
aws configure

# 4. Pull the data from S3
dvc pull

# Now they have all the artifacts!


SCENARIO C: You want to reproduce the pipeline from scratch
──────────────────────────────────────────────────────────
# Run the entire pipeline
dvc repro

# Or run a specific stage
dvc repro data_ingestion



---------------------- STEP 8: Important Files Summary ----------------------

YOUR PROJECT STRUCTURE WITH DVC:

IEEE-CIS-Fraud-detection/
├── .dvc/
│   ├── config              # Remote storage settings (COMMIT TO GIT)
│   ├── config.local        # Local credentials (DO NOT COMMIT - add in .gitignore)
│   ├── cache/              # Local cache of tracked files (DO NOT COMMIT)
│   └── .gitignore          # DVC's internal gitignore
├── artifacts/              # Your large data (TRACKED BY DVC, NOT GIT)
│   ├── data/
│   │   ├── raw/
│   │   ├── processed/
│   │   └── transformed/
│   └── .gitignore          # Created by `dvc add`, ignores contents for Git
├── artifacts.dvc           # Pointer file (COMMIT TO GIT)
├── dvc.yaml                # Pipeline definition (COMMIT TO GIT)
├── dvc.lock                # Pipeline state with hashes (COMMIT TO GIT)
└── .gitignore              # Should include artifacts/ entry



---------------------- STEP 9: Common DVC Commands Reference ----------------------

# Initialize DVC
dvc init

# Add data to DVC tracking
dvc add <path>                    # e.g., dvc add artifacts/

# Remote management
dvc remote add -d <name> <url>    # Add remote storage
dvc remote list                   # List all remotes
dvc remote remove <name>          # Remove a remote

# Data synchronization
dvc push                          # Upload to remote
dvc pull                          # Download from remote
dvc fetch                         # Download to cache only (doesn't checkout)

# Pipeline operations
dvc repro                         # Reproduce entire pipeline
dvc repro <stage>                 # Reproduce specific stage
dvc dag                           # Visualize pipeline as DAG

# Status checks
dvc status                        # Check if data is up to date
dvc diff                          # Show changes since last commit

# Configuration
dvc config core.autostage true    # Auto-stage DVC files for Git
dvc config --list                 # Show all configuration



---------------------- STEP 10: Troubleshooting ----------------------

PROBLEM: "dvc: command not found"
SOLUTION: pip install dvc[s3] and ensure pip's bin folder is in PATH

PROBLEM: "Unable to access S3 bucket"
SOLUTION: 
  - Check AWS credentials are configured: aws configure list
  - Verify bucket name is correct
  - Ensure your IAM user has S3 permissions (s3:GetObject, s3:PutObject, s3:ListBucket)

PROBLEM: "dvc push" uploads nothing
SOLUTION:
  - Run `dvc status` to check if there are changes
  - Ensure you ran `dvc add` for new files
  - Check remote is configured: `dvc remote list`

PROBLEM: Large files still being tracked by Git
SOLUTION:
  - Add the path to .gitignore BEFORE running `dvc add`
  - If already committed: git rm --cached <file>, then dvc add <file>



---------------------- YOUR S3 CREDENTIALS (Fill in before running) ----------------------

BUCKET_NAME:         ____________________________
AWS_REGION:          ____________________________
AWS_ACCESS_KEY_ID:   ____________________________
AWS_SECRET_ACCESS_KEY: __________________________


==============================================================================================
                              END OF DVC + S3 TUTORIAL
==============================================================================================




==============================================================================================
                              Model training component + mlflow (experiment tracking) + track saved model by DVC & push to s3
==============================================================================================


1. Code the model_training.py
    strategy: 
      - check schema output by data_FE_transformation.py ; save schema in schema.yaml as last step in data_FE_t..py stage, then compare while loading data from artifact/transformed

      - model training with preprocessed data set and by using model parameters listed on constants/params.yaml file.
      
      - integrate mlflow in training loop, autolog whould be better
      - save the model in models/  directory
      - dvc add models/
      - git add models.dvc  ( model.dvc created by dvc in effect of upper command)


      - add staging for model_training.py in dvc.yaml
      - dvc repro (to run the pipeline)
      - dvc push( push the model to s3)

      - retrain model applied pca on full data set, most probabity it will ruine mutliple features but this is just for experiment.

      - lets code



