# Project Setup Guide 🚀

This document explains exactly how we initialized the IEEE-CIS Fraud Detection project, from creating the environment to structuring the codebase using standard MLOps practices.

---

## 1. Environment Creation
Before writing any code, we need an isolated environment to manage dependencies. We used **Conda** for this.

```bash
# Create a new environment named 'mlops' with Python 3.10
conda create -n mlops python=3.10

# Activate the environment
conda activate mlops
```

*Why Python 3.10?* It offers a good balance of modern features and compatibility with major data science libraries like TensorFlow, PyTorch, and XGBoost.

---

## 2. Project Structure (The "Cookiecutter" Way)
Instead of creating folders manually (which is prone to error and inconsistency), we used a tool called **Cookiecutter**. This tool generates a standard Data Science project structure automatically.

### Step 2.1: Install the tool
```bash
pip install cookiecutter
```

### Step 2.2: Generate the project
We used the popular "DrivenData" data science template:

```bash
cookiecutter -c v1 https://github.com/drivendata/cookiecutter-data-science
```

**During the interactive prompt:**
- You will be asked questions like "project_name", "author_name", "python_interpreter", etc.
- **Important:** When asked about AWS/Cloud setup options, we skipped them (selected "No") because we planned to configure AWS S3 manually later for DVC.

### Step 2.3: Reorganizing
The tool creates a new folder *inside* your current directory. We moved the contents to the root level:
1. Cut all files from the generated folder.
2. Paste them into the root implementation folder (`IEEE-CIS-Fraud-detection`).
3. Renamed the `src/models` directory to `src/model` to avoid conflict with the root-level `models/` directory (where binary model files are stored).

---

## 3. Version Control (Git)
Once the structure was ready, we visualized it and initialized Git tracking.

```bash
git init
git add .
git commit -m "Initial project structure setup"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

## Resulting Structure
At the end of this phase, we had a professional folder hierarchy looking like this:

- **data/**: For raw/processed datasets (added to .gitignore)
- **notebooks/**: For experimentation
- **src/**: For production source code
- **models/**: For binary model artifacts
- **requirements.txt**: For dependencies
