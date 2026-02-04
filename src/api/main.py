"""
FastAPI Backend for IEEE-CIS Fraud Detection
=============================================
Provides REST API endpoints for batch fraud prediction using the PredictionPipeline.

Usage:
    uvicorn src.api.main:app --reload --port 8000
"""

import os
import sys
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

# Load environment variables from .env file (for local development)
# In Kubernetes/AKS: credentials are injected as env vars from secrets - these take precedence
# override=False ensures K8s-injected env vars are NOT overwritten by .env file values
from dotenv import load_dotenv
from dotenv import load_dotenv
load_dotenv(override=False)

# ============================================================================
# PROMETHEUS METRICS SETUP
# ============================================================================
from prometheus_client import (
    Counter, Histogram, Gauge,
    generate_latest, CONTENT_TYPE_LATEST, REGISTRY
)
from starlette.responses import Response
from starlette.requests import Request
import time

# ----------------------------------------------------------------------------
# LAYER 2: SERVICE METRICS (API Performance)
# ----------------------------------------------------------------------------

REQUEST_COUNT = Counter(
    'inference_requests_total',
    'Total number of inference requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'inference_request_duration_seconds',
    'Request latency in seconds',
    ['method', 'endpoint'],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)

ERROR_COUNT = Counter(
    'inference_errors_total',
    'Total number of inference errors',
    ['error_type']
)

# ----------------------------------------------------------------------------
# LAYER 3: MODEL METRICS (Fraud Detection Specific)
# ----------------------------------------------------------------------------

PREDICTIONS = Counter(
    'model_predictions_total',
    'Total predictions by result',
    ['result']  # 'fraud' or 'legitimate'
)

FRAUD_RATE = Gauge(
    'fraud_rate_percent',
    'Current fraud rate percentage (Label Drift indicator)'
)

CONFIDENCE_SCORE = Gauge(
    'model_confidence_score',
    'Average model confidence score'
)

MODEL_LOADED = Gauge(
    'model_loaded',
    'Whether model is loaded (1=yes, 0=no)'
)

BATCH_SIZE = Histogram(
    'inference_batch_size',
    'Distribution of batch sizes',
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000]
)

# ============================================================================
# DRIFT DETECTION FOR FRAUD MODEL
# ============================================================================
from scipy import stats
import numpy as np
from collections import deque

# Drift metrics
PREDICTION_DRIFT_SCORE = Gauge(
    'model_prediction_drift_score',
    'Prediction distribution drift (KS-test statistic)'
)

LABEL_DRIFT_SCORE = Gauge(
    'model_label_drift_score', 
    'Label drift from baseline fraud rate'
)

class FraudDriftDetector:
    """
    Simplified drift detection for fraud detection.
    Focuses on Prediction Drift and Label Drift.
    """
    
    def __init__(self, baseline_fraud_rate: float = 0.035, window_size: int = 1000):
        """
        Args:
            baseline_fraud_rate: Expected fraud rate from training data (3.5%)
            window_size: Number of recent predictions to analyze
        """
        self.baseline_fraud_rate = baseline_fraud_rate
        self.window_size = window_size
        
        # Sliding window of fraud probabilities
        self.prediction_window = deque(maxlen=window_size)
        
        # Reference distribution (from training)
        # Normal distribution centered around low fraud probability
        # In a real scenario, this should be loaded from the training artifact
        self.reference_distribution = np.random.beta(1, 28, size=1000)  # ~3.5% mean
    
    def add_prediction(self, fraud_probability: float):
        """Add a new prediction to the window."""
        self.prediction_window.append(fraud_probability)
    
    def add_predictions_batch(self, fraud_probabilities: list):
        """Add batch of predictions."""
        for prob in fraud_probabilities:
            self.prediction_window.append(prob)
    
    def calculate_prediction_drift(self) -> float:
        """
        Calculate prediction drift using KS-test.
        Compares current prediction distribution to reference.
        
        Returns:
            KS statistic (0-1, higher = more drift)
        """
        if len(self.prediction_window) < 100:
            return 0.0  # Not enough data
        
        current_predictions = np.array(self.prediction_window)
        
        # KS-test: compare distributions
        ks_statistic, p_value = stats.ks_2samp(
            self.reference_distribution,
            current_predictions
        )
        
        # Update Prometheus metric
        PREDICTION_DRIFT_SCORE.set(ks_statistic)
        
        return ks_statistic
    
    def calculate_label_drift(self) -> float:
        """
        Calculate label drift (change in fraud rate).
        
        Returns:
            Absolute difference from baseline
        """
        if len(self.prediction_window) < 100:
            return 0.0
        
        current_predictions = np.array(self.prediction_window)
        
        # Current fraud rate (predictions > 0.5 are fraud)
        current_fraud_rate = (current_predictions > 0.5).mean()
        
        # Drift = absolute difference from baseline
        label_drift = abs(current_fraud_rate - self.baseline_fraud_rate)
        
        # Update Prometheus metric
        LABEL_DRIFT_SCORE.set(label_drift)
        
        return label_drift
    
    def check_drift(self) -> dict:
        """
        Run all drift checks and return results.
        
        Returns:
            Dictionary with drift scores and alerts
        """
        pred_drift = self.calculate_prediction_drift()
        label_drift = self.calculate_label_drift()
        
        return {
            'prediction_drift': pred_drift,
            'prediction_drift_alert': pred_drift > 0.3,
            'label_drift': label_drift,
            'label_drift_alert': label_drift > 0.05,  # 5% deviation
            'samples_in_window': len(self.prediction_window)
        }

# Global instance (initialize at startup)
drift_detector = FraudDriftDetector(baseline_fraud_rate=0.035)

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from src.logger import logger
from src.components.prediction import PredictionPipeline
from config.config import PredictionConfig


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TransactionInput(BaseModel):
    """Single transaction input model."""
    model_config = ConfigDict(extra="allow")  # Allow extra fields for V columns and id columns

    @model_validator(mode='before')
    @classmethod
    def clean_empty_strings(cls, data: Any) -> Any:
        """
        Smart Validator:
        Converts empty strings, "null", "nan" to None.
        This allows robust handling of inference data (which may have empty strings)
        while still enforcing strict types for non-empty values (satisfying CI tests).
        """
        if isinstance(data, dict):
            for k, v in data.items():
                if isinstance(v, str):
                    v_clean = v.strip().lower()
                    if v_clean == "" or v_clean == "null" or v_clean == "nan":
                        data[k] = None
        return data
    
    TransactionID: Optional[int] = None
    TransactionDT: Optional[int] = None
    TransactionAmt: Optional[float] = None
    ProductCD: Optional[str] = None
    card1: Optional[int] = None
    card2: Optional[float] = None
    card3: Optional[float] = None
    card4: Optional[str] = None
    card5: Optional[float] = None
    card6: Optional[str] = None
    addr1: Optional[float] = None
    addr2: Optional[float] = None
    dist1: Optional[float] = None
    dist2: Optional[float] = None
    P_emaildomain: Optional[str] = None
    R_emaildomain: Optional[str] = None
    # C columns
    C1: Optional[float] = None
    C2: Optional[float] = None
    C3: Optional[float] = None
    C4: Optional[float] = None
    C5: Optional[float] = None
    C6: Optional[float] = None
    C7: Optional[float] = None
    C8: Optional[float] = None
    C9: Optional[float] = None
    C10: Optional[float] = None
    C11: Optional[float] = None
    C12: Optional[float] = None
    C13: Optional[float] = None
    C14: Optional[float] = None
    # D columns
    D1: Optional[float] = None
    D2: Optional[float] = None
    D3: Optional[float] = None
    D4: Optional[float] = None
    D5: Optional[float] = None
    D6: Optional[float] = None
    D7: Optional[float] = None
    D8: Optional[float] = None
    D9: Optional[float] = None
    D10: Optional[float] = None
    D11: Optional[float] = None
    D12: Optional[float] = None
    D13: Optional[float] = None
    D14: Optional[float] = None
    D15: Optional[float] = None
    # M columns
    M1: Optional[str] = None
    M2: Optional[str] = None
    M3: Optional[str] = None
    M4: Optional[str] = None
    M5: Optional[str] = None
    M6: Optional[str] = None
    M7: Optional[str] = None
    M8: Optional[str] = None
    M9: Optional[str] = None

# ... inside predict_batch function ...
class BatchPredictionRequest(BaseModel):
    """Batch prediction request model."""
    transactions: List[Dict[str, Any]]


class PredictionResult(BaseModel):
    """Single prediction result."""
    TransactionID: int
    isFraud: int


class BatchPredictionResponse(BaseModel):
    """Batch prediction response model."""
    predictions: List[PredictionResult]
    total: int
    fraud_count: int
    fraud_rate: float


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    model_loaded: bool
    model_version: str


# ============================================================================
# APPLICATION SETUP
# ============================================================================

# Global pipeline instance (loaded once at startup)
prediction_pipeline: Optional[PredictionPipeline] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: load model at startup."""
    global prediction_pipeline
    
    logger.info("Starting Fraud Detection API...")
    
    try:
        # Initialize prediction pipeline
        prediction_pipeline = PredictionPipeline()
        
        # Load model from S3
        logger.info("Loading model from S3...")
        prediction_pipeline.load_model()
        logger.info("✓ Model loaded successfully!")
        MODEL_LOADED.set(1)
        
    except Exception as e:
        logger.error(f"Failed to load model at startup: {str(e)}")
        logger.warning("API will start without model - /predict will fail until model is available")
        MODEL_LOADED.set(0)
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down Fraud Detection API...")


# Create FastAPI app
app = FastAPI(
    title="IEEE-CIS Fraud Detection API",
    description="Batch fraud prediction using XGBoost model loaded from S3",
    version="1.0.0",
    lifespan=lifespan
)

# ============================================================================
# METRICS ENDPOINT & MIDDLEWARE
# ============================================================================

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint - Prometheus scrapes this."""
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Automatically track latency and count for all requests."""
    start_time = time.time()
    
    response = await call_next(request)
    
    # Skip metrics for /metrics and /health endpoints to avoid noise
    if request.url.path in ["/metrics", "/health", "/favicon.ico"]:
        return response
        
    process_time = time.time() - start_time
    
    # Record metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(process_time)
    
    return response

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/", response_class=FileResponse)
async def serve_frontend():
    """Serve the frontend HTML page."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend not found")


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        model_loaded=prediction_pipeline is not None and prediction_pipeline.model is not None,
        model_version=PredictionConfig().model_version
    )


@app.post("/predict", response_model=BatchPredictionResponse)
async def predict_batch(request: BatchPredictionRequest):
    """
    Batch fraud prediction endpoint.
    
    Performs 'Smart' schema validation:
    1. Case-insensitive column matching.
    2. Data type validation using Pydantic (returns 422 on failure).
    3. Missing column handling (fills with defaults).
    """

    
    if prediction_pipeline is None or prediction_pipeline.model is None:
        raise HTTPException(
            status_code=503, 
            detail="Model not loaded. Please try again later."
        )
    
    if not request.transactions:
        raise HTTPException(
            status_code=400,
            detail="No transactions provided"
        )
    
    try:
        logger.info(f"Received batch prediction request with {len(request.transactions)} transactions")
        
        # Track batch size
        BATCH_SIZE.observe(len(request.transactions))
        
        # --- PHASE 1: SMART MAPPING & VALIDATION ---
        validated_transactions = []
        reference_keys = TransactionInput.model_fields.keys()
        key_map = {k.lower(): k for k in reference_keys}
        
        for idx, raw_tx in enumerate(request.transactions):
            # Normalize keys (casing)
            normalized_tx = {}
            for k, v in raw_tx.items():
                k_norm = k.lower().strip()
                if k_norm in key_map:
                    normalized_tx[key_map[k_norm]] = v
                else:
                    normalized_tx[k] = v # Keep extra columns as-is
            
            # --- VALIDATION ---
            # Strictly validate types using the Pydantic model.
            # This ensures "garbage" strings for numeric fields trigger a 422 Error.
            try:
                validated_item = TransactionInput(**normalized_tx)
                # Convert back to dict for DataFrame processing
                validated_transactions.append(validated_item.model_dump()) 
            except ValidationError as e:
                logger.warning(f"Validation failed for row {idx}: {e}")
                raise HTTPException(
                    status_code=422, 
                    detail=f"Validation error in row {idx}: {e.errors()}"
                )
        
        # --- PHASE 2: PREDICTION ---
        df = pd.DataFrame(validated_transactions)
        
        # Ensure TransactionID exists (Pydantic might have set it to None if optional)
        if 'TransactionID' not in df.columns or df['TransactionID'].isnull().all():
            logger.warning("TransactionID missing or null, generating sequential IDs.")
            df['TransactionID'] = range(1, len(df) + 1)
        
        # Run prediction pipeline (use predict_proba to get scores)
        result_df = prediction_pipeline.predict_proba(df)
        
        # Convert to response format
        predictions = []
        confidences = []
        drift_values = []
        
        for _, row in result_df.iterrows():
            is_fraud = int(row['prediction_isFraud'])
            prob = float(row['fraud_probability'])
            
            # Confidence is probability of the predicted class
            confidence = prob if is_fraud == 1 else (1.0 - prob)
            
            predictions.append(
                PredictionResult(
                    TransactionID=int(row['TransactionID']),
                    isFraud=is_fraud
                )
            )
            confidences.append(confidence)
            drift_values.append(prob)
        
        fraud_count = sum(1 for p in predictions if p.isFraud == 1)
        fraud_rate = (fraud_count / len(predictions) * 100) if predictions else 0
        
        # UPDATE METRICS
        legit_count = len(predictions) - fraud_count
        PREDICTIONS.labels(result='fraud').inc(fraud_count)
        PREDICTIONS.labels(result='legitimate').inc(legit_count)
        FRAUD_RATE.set(fraud_rate)
        
        if confidences:
            avg_confidence = sum(confidences) / len(confidences)
            CONFIDENCE_SCORE.set(avg_confidence)
        
        # Update rolling window for drift detection (using probabilities)
        # Add to drift detector
        drift_detector.add_predictions_batch(drift_values)
        
        # Periodically check drift (every 100 predictions)
        if len(drift_detector.prediction_window) % 100 == 0:
            drift_results = drift_detector.check_drift()
            if drift_results['prediction_drift_alert']:
                logger.warning(f"⚠️ Prediction drift detected: {drift_results['prediction_drift']:.3f} (KS Test)")
            if drift_results['label_drift_alert']:
                logger.warning(f"⚠️ Label drift detected: {drift_results['label_drift']:.3f} (Fraud Rate Deviation)")
            
            # Log drift metrics for debugging
            logger.info(f"Drift Check - Pred Drift: {drift_results['prediction_drift']:.3f}, Label Drift: {drift_results['label_drift']:.3f}")

        logger.info(f"✓ Batch prediction complete: {len(predictions)} transactions, {fraud_count} fraud")
        
        return BatchPredictionResponse(
            predictions=predictions,
            total=len(predictions),
            fraud_count=fraud_count,
            fraud_rate=round(fraud_rate, 2)
        )
        
    except HTTPException:
        raise # Re-raise validation errors
    except Exception as e:
        ERROR_COUNT.labels(error_type=type(e).__name__).inc()
        logger.error(f"Prediction failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/predict/simple")
async def predict_simple(transactions: List[Dict[str, Any]]):
    """
    Simplified prediction endpoint - accepts raw JSON array directly.
    """
    return await predict_batch(BatchPredictionRequest(transactions=transactions))


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
