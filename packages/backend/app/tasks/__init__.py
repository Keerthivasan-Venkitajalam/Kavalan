# Celery tasks package

from app.tasks.audio_tasks import analyze_audio
from app.tasks.visual_tasks import analyze_visual_task
from app.tasks.liveness_tasks import analyze_liveness_task
from app.tasks.fir_tasks import generate_fir_task
from app.tasks.threat_fusion_tasks import fuse_and_generate_fir

__all__ = [
    'analyze_audio',
    'analyze_visual_task',
    'analyze_liveness_task',
    'generate_fir_task',
    'fuse_and_generate_fir'
]
