#!/bin/bash
set -e  # Exit on error

echo "🚀 Starting Training Pipeline..."

# Initialize dummy git repo for DVC (required if .git is not copied)
if [ ! -d ".git" ]; then
    echo "🔧 Initializing dummy git repo..."
    git init
    git config user.email "ci@example.com"
    git config user.name "CI Runner"
    # DVC expects to be in a git repo
fi

# Configure DagsHub/MLflow credentials (for experiment tracking)
if [ -n "$DAGSHUB_TOKEN" ]; then
    export DAGSHUB_USER_TOKEN=$DAGSHUB_TOKEN
    echo "✓ DagsHub authentication configured"
else
    echo "⚠ Warning: DAGSHUB_TOKEN not set, MLflow tracking may fail"
fi

# Configure DVC with AWS credentials (passed from GitHub Actions → Docker)
dvc remote modify s3remote access_key_id $AWS_ACCESS_KEY_ID
dvc remote modify s3remote secret_access_key $AWS_SECRET_ACCESS_KEY

# Pull cached data (if any)
echo "📥 Pulling cached data..."
dvc pull --allow-missing --force || true

# Run training pipeline
echo "⚙️ Running DVC pipeline..."
dvc repro --force

# Push new artifacts (model) to S3
echo "📤 Pushing artifacts to S3..."
dvc push

echo "✅ Training complete!"