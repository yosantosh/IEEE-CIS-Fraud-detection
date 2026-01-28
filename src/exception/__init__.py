"""
Custom Exception Module for IEEE-CIS Fraud Detection Pipeline

This module provides reusable custom exceptions for all pipeline components
including data ingestion, transformation, feature engineering, model training, etc.

Usage:
    from src.exception import CustomException
    
    try:
        # your code
    except Exception as e:
        raise CustomException(e, sys)
"""

import sys
from typing import Optional


def get_error_details(error: Exception, error_detail: sys) -> str:
    """
    Extract detailed error information including file name, line number, and error message.
    
    Args:
        error (Exception): The original exception that was raised
        error_detail (sys): The sys module to access exception info
        
    Returns:
        str: Formatted error message with file name, line number, and error details
    """
    # Get exception traceback info
    _, _, exc_tb = error_detail.exc_info()
    
    if exc_tb is not None:
        # Get the file name where exception occurred
        file_name = exc_tb.tb_frame.f_code.co_filename
        # Get the line number where exception occurred
        line_number = exc_tb.tb_lineno
        
        error_message = (
            f"\n{'='*60}\n"
            f"🚨 EXCEPTION OCCURRED\n"
            f"{'='*60}\n"
            f"📁 File: {file_name}\n"
            f"📍 Line: {line_number}\n"
            f"❌ Error: {str(error)}\n"
            f"{'='*60}"
        )
    else:
        error_message = f"Error: {str(error)}"
    
    return error_message


class CustomException(Exception):
    """
    Custom Exception class for the IEEE-CIS Fraud Detection Pipeline.
    
    This exception captures detailed error information including the file name,
    line number, and original error message. Use this as the base exception
    for all pipeline components.
    
    Usage:
        from src.exception import CustomException
        import sys
        
        try:
            # your risky code here
            result = some_function()
        except Exception as e:
            raise CustomException(e, sys)
    
    Attributes:
        error_message (str): Detailed formatted error message
    """
    
    def __init__(self, error_message: Exception, error_detail: sys):
        """
        Initialize the CustomException.
        
        Args:
            error_message (Exception): The original exception
            error_detail (sys): The sys module for accessing traceback info
        """
        super().__init__(str(error_message))
        self.error_message = get_error_details(error_message, error_detail)
    
    def __str__(self) -> str:
        """Return the formatted error message."""
        return self.error_message


# ============================================================================
# PIPELINE-SPECIFIC EXCEPTIONS
# ============================================================================
# These specialized exceptions inherit from CustomException and can be used
# for more granular error handling in specific pipeline stages.

class DataIngestionException(CustomException):
    """Exception raised during data ingestion operations."""
    
    def __init__(self, error_message: Exception, error_detail: sys):
        super().__init__(error_message, error_detail)
        self.error_message = f"[DATA INGESTION] {self.error_message}"


class DataTransformationException(CustomException):
    """Exception raised during data transformation operations."""
    
    def __init__(self, error_message: Exception, error_detail: sys):
        super().__init__(error_message, error_detail)
        self.error_message = f"[DATA TRANSFORMATION] {self.error_message}"


class FeatureEngineeringException(CustomException):
    """Exception raised during feature engineering operations."""
    
    def __init__(self, error_message: Exception, error_detail: sys):
        super().__init__(error_message, error_detail)
        self.error_message = f"[FEATURE ENGINEERING] {self.error_message}"


class ModelTrainingException(CustomException):
    """Exception raised during model training operations."""
    
    def __init__(self, error_message: Exception, error_detail: sys):
        super().__init__(error_message, error_detail)
        self.error_message = f"[MODEL TRAINING] {self.error_message}"


class ModelEvaluationException(CustomException):
    """Exception raised during model evaluation operations."""
    
    def __init__(self, error_message: Exception, error_detail: sys):
        super().__init__(error_message, error_detail)
        self.error_message = f"[MODEL EVALUATION] {self.error_message}"


class ModelPredictionException(CustomException):
    """Exception raised during model prediction/inference operations."""
    
    def __init__(self, error_message: Exception, error_detail: sys):
        super().__init__(error_message, error_detail)
        self.error_message = f"[MODEL PREDICTION] {self.error_message}"


class ConfigurationException(CustomException):
    """Exception raised for configuration-related errors."""
    
    def __init__(self, error_message: Exception, error_detail: sys):
        super().__init__(error_message, error_detail)
        self.error_message = f"[CONFIGURATION] {self.error_message}"


class ValidationException(CustomException):
    """Exception raised during data/schema validation operations."""
    
    def __init__(self, error_message: Exception, error_detail: sys):
        super().__init__(error_message, error_detail)
        self.error_message = f"[VALIDATION] {self.error_message}"
