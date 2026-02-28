"""
Worker health monitoring and failover logic

This module provides health monitoring for Celery workers to support
automatic failover when workers fail.
"""
from app.celery_app import celery_app
from celery import current_app
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class WorkerHealthMonitor:
    """
    Monitor worker health and detect failed workers for failover.
    
    Celery provides built-in failover through:
    1. task_acks_late: Tasks are acknowledged only after completion
    2. task_reject_on_worker_lost: Tasks are requeued if worker dies
    3. Worker heartbeats: Workers send periodic heartbeats to broker
    
    This class provides additional monitoring and logging capabilities.
    """
    
    def __init__(self, app=None):
        self.app = app or celery_app
        
    def get_active_workers(self) -> Dict[str, Dict]:
        """
        Get list of active workers from Celery.
        
        Returns:
            Dict mapping worker names to their stats
        """
        try:
            inspect = self.app.control.inspect()
            stats = inspect.stats()
            
            if stats is None:
                logger.warning("No workers available or broker unreachable")
                return {}
            
            logger.info(f"Found {len(stats)} active workers")
            return stats
        except Exception as e:
            logger.error(f"Failed to get active workers: {e}")
            return {}
    
    def get_worker_queues(self) -> Dict[str, List[str]]:
        """
        Get the queues each worker is consuming from.
        
        Returns:
            Dict mapping worker names to list of queue names
        """
        try:
            inspect = self.app.control.inspect()
            active_queues = inspect.active_queues()
            
            if active_queues is None:
                logger.warning("No worker queues available")
                return {}
            
            # Extract queue names for each worker
            worker_queues = {}
            for worker, queues in active_queues.items():
                worker_queues[worker] = [q['name'] for q in queues]
            
            return worker_queues
        except Exception as e:
            logger.error(f"Failed to get worker queues: {e}")
            return {}
    
    def check_worker_health(self, worker_name: str) -> bool:
        """
        Check if a specific worker is healthy by pinging it.
        
        Args:
            worker_name: Name of the worker to check
            
        Returns:
            True if worker responds to ping, False otherwise
        """
        try:
            inspect = self.app.control.inspect([worker_name])
            ping_result = inspect.ping()
            
            if ping_result and worker_name in ping_result:
                logger.debug(f"Worker {worker_name} is healthy")
                return True
            else:
                logger.warning(f"Worker {worker_name} did not respond to ping")
                return False
        except Exception as e:
            logger.error(f"Failed to ping worker {worker_name}: {e}")
            return False
    
    def get_queue_health(self, queue_name: str) -> Dict:
        """
        Get health status for a specific queue.
        
        Args:
            queue_name: Name of the queue to check
            
        Returns:
            Dict with queue health information
        """
        try:
            # Get workers consuming from this queue
            worker_queues = self.get_worker_queues()
            workers_for_queue = [
                worker for worker, queues in worker_queues.items()
                if queue_name in queues
            ]
            
            # Check health of each worker
            healthy_workers = []
            failed_workers = []
            
            for worker in workers_for_queue:
                if self.check_worker_health(worker):
                    healthy_workers.append(worker)
                else:
                    failed_workers.append(worker)
            
            health_status = {
                'queue_name': queue_name,
                'total_workers': len(workers_for_queue),
                'healthy_workers': len(healthy_workers),
                'failed_workers': len(failed_workers),
                'healthy_worker_names': healthy_workers,
                'failed_worker_names': failed_workers,
                'has_capacity': len(healthy_workers) > 0
            }
            
            if failed_workers:
                logger.warning(
                    f"Queue {queue_name} has {len(failed_workers)} failed workers: "
                    f"{failed_workers}"
                )
            
            return health_status
        except Exception as e:
            logger.error(f"Failed to get queue health for {queue_name}: {e}")
            return {
                'queue_name': queue_name,
                'error': str(e),
                'has_capacity': False
            }
    
    def get_all_queue_health(self) -> Dict[str, Dict]:
        """
        Get health status for all queues.
        
        Returns:
            Dict mapping queue names to their health status
        """
        queues = ['audio_queue', 'visual_queue', 'liveness_queue']
        health_status = {}
        
        for queue in queues:
            health_status[queue] = self.get_queue_health(queue)
        
        return health_status
    
    def log_worker_status(self):
        """
        Log current worker status for monitoring.
        """
        try:
            workers = self.get_active_workers()
            queue_health = self.get_all_queue_health()
            
            logger.info("=== Worker Status Report ===")
            logger.info(f"Total active workers: {len(workers)}")
            
            for queue_name, health in queue_health.items():
                logger.info(
                    f"Queue {queue_name}: "
                    f"{health.get('healthy_workers', 0)}/{health.get('total_workers', 0)} "
                    f"healthy workers"
                )
                
                if not health.get('has_capacity', False):
                    logger.error(f"CRITICAL: Queue {queue_name} has no healthy workers!")
            
            logger.info("=== End Worker Status Report ===")
        except Exception as e:
            logger.error(f"Failed to log worker status: {e}")


# Global health monitor instance
health_monitor = WorkerHealthMonitor()


@celery_app.task(bind=True)
def monitor_worker_health(self):
    """
    Periodic task to monitor worker health and log status.
    
    This task should be scheduled to run periodically (e.g., every 60 seconds)
    to monitor worker health and detect failures.
    """
    try:
        health_monitor.log_worker_status()
        return {"status": "success", "timestamp": self.request.id}
    except Exception as e:
        logger.error(f"Worker health monitoring failed: {e}")
        return {"status": "error", "error": str(e)}
