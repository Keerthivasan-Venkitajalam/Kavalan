"""
Celery Queue and Worker Monitoring

Provides utilities to monitor Celery queue depth and worker utilization.
Implements Requirement 9.4: Track end-to-end latency and monitor queue depth.
"""
from celery import Celery
from celery.app.control import Inspect
from typing import Dict, List
import logging
from app.utils.metrics import (
    update_queue_depth,
    update_worker_count,
    update_worker_utilization,
    track_celery_task
)

logger = logging.getLogger(__name__)


class CeleryMonitor:
    """Monitor Celery queue depth and worker metrics"""
    
    def __init__(self, celery_app: Celery):
        self.celery_app = celery_app
        self.inspector = Inspect(app=celery_app)
    
    def get_queue_depths(self) -> Dict[str, int]:
        """
        Get the number of tasks in each queue
        
        Returns:
            Dictionary mapping queue names to task counts
        """
        try:
            # Get active tasks
            active = self.inspector.active()
            # Get reserved tasks (prefetched but not yet executing)
            reserved = self.inspector.reserved()
            # Get scheduled tasks
            scheduled = self.inspector.scheduled()
            
            queue_depths = {}
            
            # Count tasks by queue
            for worker_name, tasks in (active or {}).items():
                for task in tasks:
                    queue = task.get('delivery_info', {}).get('routing_key', 'default')
                    queue_depths[queue] = queue_depths.get(queue, 0) + 1
            
            for worker_name, tasks in (reserved or {}).items():
                for task in tasks:
                    queue = task.get('delivery_info', {}).get('routing_key', 'default')
                    queue_depths[queue] = queue_depths.get(queue, 0) + 1
            
            for worker_name, tasks in (scheduled or {}).items():
                for task in tasks:
                    queue = task.get('delivery_info', {}).get('routing_key', 'default')
                    queue_depths[queue] = queue_depths.get(queue, 0) + 1
            
            # Update Prometheus metrics
            for queue_name, depth in queue_depths.items():
                update_queue_depth(queue_name, depth)
            
            return queue_depths
        
        except Exception as e:
            logger.error(f"Failed to get queue depths: {e}")
            return {}
    
    def get_worker_stats(self) -> Dict[str, Dict]:
        """
        Get worker statistics including active worker count and utilization
        
        Returns:
            Dictionary with worker statistics
        """
        try:
            # Get active workers
            active_workers = self.inspector.active()
            stats = self.inspector.stats()
            
            if not active_workers:
                update_worker_count(0)
                return {}
            
            # Update active worker count
            worker_count = len(active_workers)
            update_worker_count(worker_count)
            
            worker_stats = {}
            
            for worker_name, tasks in active_workers.items():
                # Get worker pool size from stats
                worker_pool_size = 1
                if stats and worker_name in stats:
                    worker_pool_size = stats[worker_name].get('pool', {}).get('max-concurrency', 1)
                
                # Calculate utilization
                active_task_count = len(tasks)
                utilization = (active_task_count / worker_pool_size) * 100 if worker_pool_size > 0 else 0
                
                worker_stats[worker_name] = {
                    'active_tasks': active_task_count,
                    'pool_size': worker_pool_size,
                    'utilization': utilization
                }
                
                # Update Prometheus metrics
                update_worker_utilization(worker_name, utilization)
            
            return worker_stats
        
        except Exception as e:
            logger.error(f"Failed to get worker stats: {e}")
            return {}
    
    def get_all_metrics(self) -> Dict:
        """
        Get all Celery metrics (queue depths and worker stats)
        
        Returns:
            Dictionary with all metrics
        """
        return {
            'queue_depths': self.get_queue_depths(),
            'worker_stats': self.get_worker_stats()
        }


def track_task_execution(task_name: str, status: str, duration: float = None):
    """
    Track Celery task execution metrics
    
    Args:
        task_name: Name of the task
        status: Task status (success, failure, retry)
        duration: Task execution duration in seconds
    """
    track_celery_task(task_name, status, duration)
