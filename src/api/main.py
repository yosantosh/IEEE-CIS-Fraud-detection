"""
FastAPI Backend for IEEE-CIS Fraud Detection
=============================================
Provides REST API endpoints for batch fraud prediction using the PredictionPipeline.

Usage:
    uvicorn src.api.main:app --reload --port 8000
"""

import os
import sys
import yaml
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.logger import logger
from src.components.prediction import PredictionPipeline
from config.config import PredictionConfig


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class TransactionInput(BaseModel):
    """Single transaction input model."""
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
    
    class Config:
        extra = "allow"  # Allow extra fields for V columns and id columns


class BatchPredictionRequest(BaseModel):
    """Batch prediction request model."""
    transactions: List[TransactionInput]


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
        
    except Exception as e:
        logger.error(f"Failed to load model at startup: {str(e)}")
        logger.warning("API will start without model - /predict will fail until model is available")
    
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
    
    Accepts a list of transactions and returns predictions with TransactionID and isFraud.
    """
    # prediction_pipeline is defined at module level and only read here, so global keyword is not needed and triggers flake8 F824
    
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
        
        # Convert to DataFrame
        df = pd.DataFrame([t.model_dump() for t in request.transactions])
        
        # Ensure TransactionID exists
        if 'TransactionID' not in df.columns:
            df['TransactionID'] = range(1, len(df) + 1)
        
        # [AUTOPATCH] Load schema to identify missing columns and fill them with None (permisssive mode)
        pred_config = PredictionConfig()
        if os.path.exists(pred_config.schema_yaml_path):
            try:
                with open(pred_config.schema_yaml_path, 'r') as f:
                    schema_data = yaml.safe_load(f) or {}
                
                if pred_config.raw_schema_name in schema_data:
                    raw_schema = schema_data[pred_config.raw_schema_name]
                    # Get list of expected columns
                    expected_cols = list(raw_schema.keys())
                    
                    # Exclude target column
                    if pred_config.target_column in expected_cols:
                        expected_cols.remove(pred_config.target_column)
                    
                    # Identify missing columns
                    missing_cols = [c for c in expected_cols if c not in df.columns]
                    
                    if missing_cols:
                        logger.info(f"Filling {len(missing_cols)} missing columns (schema mismatch) with None for inference")
                        # Add missing columns efficiently
                        # Using pd.concat or reindex might be cleaner but assigning None works
                        for col in missing_cols:
                            df[col] = None
            except Exception as e:
                 logger.warning(f"Schema auto-fill failed: {e}")
        
        # Run prediction pipeline
        result_df = prediction_pipeline.predict(df)
        
        # Convert to response format
        predictions = [
            PredictionResult(
                TransactionID=int(row['TransactionID']),
                isFraud=int(row['prediction_isFraud'])
            )
            for _, row in result_df.iterrows()
        ]
        
        fraud_count = sum(1 for p in predictions if p.isFraud == 1)
        fraud_rate = (fraud_count / len(predictions) * 100) if predictions else 0
        
        logger.info(f"✓ Batch prediction complete: {len(predictions)} transactions, {fraud_count} fraud")
        
        return BatchPredictionResponse(
            predictions=predictions,
            total=len(predictions),
            fraud_count=fraud_count,
            fraud_rate=round(fraud_rate, 2)
        )
        
    except Exception as e:
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
