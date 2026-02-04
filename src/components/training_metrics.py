"""
Training Metrics - Push to Prometheus Pushgateway
=================================================
Training jobs run and exit, so we PUSH metrics before the job dies.
"""

import os
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

class TrainingMetrics:
    """Push training metrics to Prometheus Pushgateway."""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        
        # Pushgateway URL (inside Kubernetes)
        self.pushgateway_url = os.getenv(
            'PUSHGATEWAY_URL',
            'pushgateway-prometheus-pushgateway.monitoring.svc.cluster.local:9091'
        )
        self.job_name = 'fraud_training_job'
        
        # Training job metrics
        self.duration = Gauge(
            'training_duration_seconds',
            'Duration of training job in seconds',
            registry=self.registry
        )
        self.status = Gauge(
            'training_status',
            'Training job status (1=success, 0=failure)',
            registry=self.registry
        )
        self.rows_processed = Gauge(
            'training_data_rows_processed',
            'Number of rows processed during training',
            registry=self.registry
        )
        
        # Model performance metrics
        self.accuracy = Gauge('model_accuracy', 'Accuracy', registry=self.registry)
        self.precision = Gauge('model_precision', 'Precision', registry=self.registry)
        self.recall = Gauge('model_recall', 'Recall', registry=self.registry)
        self.f1 = Gauge('model_f1_score', 'F1 Score', registry=self.registry)
        self.auc_roc = Gauge('model_auc_roc', 'AUC-ROC', registry=self.registry)
    
    def record_training_result(
        self,
        duration_seconds: float,
        success: bool,
        rows_processed: int,
        accuracy: float = None,
        precision: float = None,
        recall: float = None,
        f1: float = None,
        auc_roc: float = None
    ):
        """Record metrics and push to Pushgateway."""
        # Set metric values
        self.duration.set(duration_seconds)
        self.status.set(1 if success else 0)
        self.rows_processed.set(rows_processed)
        
        if accuracy is not None:
            self.accuracy.set(accuracy)
        if precision is not None:
            self.precision.set(precision)
        if recall is not None:
            self.recall.set(recall)
        if f1 is not None:
            self.f1.set(f1)
        if auc_roc is not None:
            self.auc_roc.set(auc_roc)
        
        # PUSH to gateway
        try:
            push_to_gateway(
                self.pushgateway_url,
                job=self.job_name,
                registry=self.registry
            )
            print(f"✅ Metrics pushed to Pushgateway: {self.pushgateway_url}")
        except Exception as e:
            print(f"⚠️ Failed to push metrics to Pushgateway: {e}")
