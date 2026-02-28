"""
Celery application configuration with Redis broker and task queues
"""
from celery import Celery
from app.config import settings
import logging

logger = logging.getLogger(__name__)

# Initialize Celery app with Redis broker
celery_app = Celery(
    "kavalan",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.audio_tasks",
        "app.tasks.visual_tasks",
        "app.tasks.liveness_tasks",
        "app.tasks.worker_health",
        "app.tasks.fir_tasks",
        "app.tasks.threat_fusion_tasks",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone
    timezone="Asia/Kolkata",
    enable_utc=True,
    
    # Task execution
    task_track_started=True,
    task_time_limit=30,  # Hard timeout (kills task after 30s)
    task_soft_time_limit=25,  # Soft timeout for graceful handling (25s)
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,  # Requeue if worker dies
    task_ignore_result=False,  # Store task results
    
    # Worker configuration
    worker_prefetch_multiplier=4,  # Number of tasks to prefetch
    worker_max_tasks_per_child=1000,  # Restart worker after N tasks
    worker_disable_rate_limits=False,
    worker_send_task_events=True,  # Enable task events for monitoring
    worker_pool_restarts=True,  # Enable pool restarts on failure
    
    # Result backend
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,  # Persist results to disk
    
    # Retry configuration
    task_default_retry_delay=2,  # Default retry delay (seconds)
    task_max_retries=3,  # Maximum retry attempts
    
    # Broker configuration
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,
    broker_heartbeat=30,  # Send heartbeat every 30 seconds
    broker_heartbeat_checkrate=2,  # Check heartbeat every 2 iterations
    
    # Task events for monitoring
    task_send_sent_event=True,
    
    # Worker failover configuration
    worker_cancel_long_running_tasks_on_connection_loss=True,  # Cancel long tasks on disconnect
)

# Task routing - distribute tasks to specific queues
celery_app.conf.task_routes = {
    "app.tasks.audio_tasks.*": {"queue": "audio_queue"},
    "app.tasks.visual_tasks.*": {"queue": "visual_queue"},
    "app.tasks.liveness_tasks.*": {"queue": "liveness_queue"},
    "app.tasks.fir_tasks.*": {"queue": "fir_queue"},
    "app.tasks.threat_fusion_tasks.*": {"queue": "fusion_queue"},
}

# Queue definitions with priorities
celery_app.conf.task_queues = {
    "audio_queue": {
        "exchange": "audio",
        "routing_key": "audio",
    },
    "visual_queue": {
        "exchange": "visual",
        "routing_key": "visual",
    },
    "liveness_queue": {
        "exchange": "liveness",
        "routing_key": "liveness",
    },
    "fir_queue": {
        "exchange": "fir",
        "routing_key": "fir",
    },
    "fusion_queue": {
        "exchange": "fusion",
        "routing_key": "fusion",
    },
}

# Default queue
celery_app.conf.task_default_queue = "audio_queue"
celery_app.conf.task_default_exchange = "default"
celery_app.conf.task_default_routing_key = "default"

logger.info("Celery app configured with Redis broker and task queues")

# Initialize OpenTelemetry tracing for Celery workers
# This will be called when workers start
def init_celery_tracing():
    """Initialize tracing for Celery workers"""
    try:
        from app.utils.tracing import initialize_tracing, instrument_celery
        import os
        
        otlp_endpoint = os.getenv("OTLP_ENDPOINT")
        enable_console = os.getenv("ENVIRONMENT") == "development"
        
        initialize_tracing(
            service_name="kavalan-celery-worker",
            service_version="1.0.0",
            otlp_endpoint=otlp_endpoint,
            enable_console_export=enable_console
        )
        
        instrument_celery()
        
        logger.info("OpenTelemetry tracing initialized for Celery workers")
    except Exception as e:
        logger.warning(f"Failed to initialize tracing for Celery: {e}")

# Register worker initialization hook
@celery_app.on_after_configure.connect
def setup_tracing(sender, **kwargs):
    """Setup tracing when Celery worker starts"""
    init_celery_tracing()

