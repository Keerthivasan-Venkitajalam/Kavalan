"""
Integration test to verify parallel processing of inference engines.

This test validates Property 10: Parallel Modality Processing
For any captured media sample, audio transcription, visual analysis, 
and liveness detection should execute in parallel (concurrent execution, not sequential).
"""

import pytest
import asyncio
import time
import numpy as np
from PIL import Image
import io

from app.services.audio_transcriber import AudioTranscriber
from app.services.visual_analyzer import VisualAnalyzer
from app.services.liveness_detector import LivenessDetector


def create_test_audio(duration_seconds: float = 1.0, sample_rate: int = 16000) -> np.ndarray:
    """Create test audio data."""
    num_samples = int(duration_seconds * sample_rate)
    # Generate simple sine wave
    t = np.linspace(0, duration_seconds, num_samples)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32)
    return audio


def create_test_frame(width: int = 640, height: int = 480) -> bytes:
    """Create test video frame."""
    # Create a simple test image
    image = Image.new('RGB', (width, height), color='white')
    buffer = io.BytesIO()
    image.save(buffer, format='JPEG')
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_parallel_inference_execution():
    """
    Test that audio, visual, and liveness inference engines can execute in parallel.
    
    This validates that the three modalities process concurrently rather than sequentially.
    If they run in parallel, total time should be close to the slowest individual task,
    not the sum of all tasks.
    """
    # Initialize services
    audio_transcriber = AudioTranscriber(model_size='tiny')
    visual_analyzer = VisualAnalyzer(api_key='test-key')  # Mock API key for testing
    liveness_detector = LivenessDetector()
    
    # Prepare test data
    test_audio = create_test_audio(duration_seconds=1.0)
    test_frame = create_test_frame()
    
    # Measure sequential execution time
    start_sequential = time.time()
    
    # Audio processing
    audio_start = time.time()
    audio_result = audio_transcriber.transcribe(test_audio)
    audio_time = time.time() - audio_start
    
    # Visual processing (mock - no actual API call)
    visual_start = time.time()
    visual_result = visual_analyzer.calculate_score({
        'uniform_detected': False,
        'badge_detected': False,
        'threats': [],
        'text_detected': '',
        'confidence': 0.8
    })
    visual_time = time.time() - visual_start
    
    # Liveness processing
    liveness_start = time.time()
    liveness_result = liveness_detector.detect_liveness(test_frame)
    liveness_time = time.time() - liveness_start
    
    sequential_time = time.time() - start_sequential
    
    print(f"\n=== Sequential Execution ===")
    print(f"Audio time: {audio_time:.3f}s")
    print(f"Visual time: {visual_time:.3f}s")
    print(f"Liveness time: {liveness_time:.3f}s")
    print(f"Total sequential time: {sequential_time:.3f}s")
    
    # Measure parallel execution time using asyncio
    async def process_audio():
        return audio_transcriber.transcribe(test_audio)
    
    async def process_visual():
        return visual_analyzer.calculate_score({
            'uniform_detected': False,
            'badge_detected': False,
            'threats': [],
            'text_detected': '',
            'confidence': 0.8
        })
    
    async def process_liveness():
        return liveness_detector.detect_liveness(test_frame)
    
    start_parallel = time.time()
    
    # Execute all three in parallel
    results = await asyncio.gather(
        asyncio.to_thread(process_audio),
        asyncio.to_thread(process_visual),
        asyncio.to_thread(process_liveness)
    )
    
    parallel_time = time.time() - start_parallel
    
    print(f"\n=== Parallel Execution ===")
    print(f"Total parallel time: {parallel_time:.3f}s")
    print(f"Speedup: {sequential_time / parallel_time:.2f}x")
    
    # Verify results are valid
    audio_result_parallel, visual_result_parallel, liveness_result_parallel = results
    
    assert audio_result_parallel is not None
    assert 'text' in audio_result_parallel
    assert visual_result_parallel >= 0.0
    assert liveness_result_parallel is not None
    assert 'face_detected' in liveness_result_parallel
    
    # Verify parallel execution is faster than sequential
    # Allow some overhead, but parallel should be at least 1.2x faster for real parallelism
    # (conservative threshold to account for overhead and test environment variability)
    assert parallel_time < sequential_time * 0.9, \
        f"Parallel execution ({parallel_time:.3f}s) should be faster than sequential ({sequential_time:.3f}s)"
    
    print(f"\n✓ Parallel processing validated: {parallel_time:.3f}s vs {sequential_time:.3f}s")


@pytest.mark.asyncio
async def test_concurrent_task_execution():
    """
    Test that multiple inference tasks can be submitted concurrently.
    
    This simulates the real-world scenario where multiple media samples
    arrive and need to be processed simultaneously.
    """
    audio_transcriber = AudioTranscriber(model_size='tiny')
    visual_analyzer = VisualAnalyzer(api_key='test-key')  # Mock API key for testing
    liveness_detector = LivenessDetector()
    
    # Create multiple test samples
    num_samples = 3
    audio_samples = [create_test_audio() for _ in range(num_samples)]
    frame_samples = [create_test_frame() for _ in range(num_samples)]
    
    async def process_sample(idx: int):
        """Process one complete sample (audio + visual + liveness)."""
        audio_task = asyncio.to_thread(
            audio_transcriber.transcribe, 
            audio_samples[idx]
        )
        visual_task = asyncio.to_thread(
            visual_analyzer.calculate_score,
            {
                'uniform_detected': False,
                'badge_detected': False,
                'threats': [],
                'text_detected': '',
                'confidence': 0.8
            }
        )
        liveness_task = asyncio.to_thread(
            liveness_detector.detect_liveness,
            frame_samples[idx]
        )
        
        return await asyncio.gather(audio_task, visual_task, liveness_task)
    
    start = time.time()
    
    # Process all samples concurrently
    all_results = await asyncio.gather(*[
        process_sample(i) for i in range(num_samples)
    ])
    
    total_time = time.time() - start
    
    print(f"\n=== Concurrent Sample Processing ===")
    print(f"Processed {num_samples} samples in {total_time:.3f}s")
    print(f"Average time per sample: {total_time / num_samples:.3f}s")
    
    # Verify all results are valid
    assert len(all_results) == num_samples
    for idx, (audio_result, visual_result, liveness_result) in enumerate(all_results):
        assert audio_result is not None, f"Sample {idx}: audio result is None"
        assert visual_result >= 0.0, f"Sample {idx}: invalid visual score"
        assert liveness_result is not None, f"Sample {idx}: liveness result is None"
    
    print(f"✓ All {num_samples} samples processed successfully in parallel")


def test_inference_engines_are_thread_safe():
    """
    Test that inference engines can be safely used from multiple threads.
    
    This is important for parallel processing in production.
    """
    import concurrent.futures
    
    audio_transcriber = AudioTranscriber(model_size='tiny')
    visual_analyzer = VisualAnalyzer(api_key='test-key')  # Mock API key for testing
    liveness_detector = LivenessDetector()
    
    def process_audio_sample(sample_id: int):
        audio = create_test_audio()
        result = audio_transcriber.transcribe(audio)
        return sample_id, 'audio', result
    
    def process_visual_sample(sample_id: int):
        score = visual_analyzer.calculate_score({
            'uniform_detected': False,
            'badge_detected': False,
            'threats': [],
            'text_detected': '',
            'confidence': 0.8
        })
        return sample_id, 'visual', score
    
    def process_liveness_sample(sample_id: int):
        frame = create_test_frame()
        result = liveness_detector.detect_liveness(frame)
        return sample_id, 'liveness', result
    
    # Submit tasks to thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = []
        
        # Submit 2 samples for each modality
        for i in range(2):
            futures.append(executor.submit(process_audio_sample, i))
            futures.append(executor.submit(process_visual_sample, i))
            futures.append(executor.submit(process_liveness_sample, i))
        
        # Wait for all to complete
        results = [f.result() for f in concurrent.futures.as_completed(futures)]
    
    # Verify all completed successfully
    assert len(results) == 6
    
    audio_results = [r for r in results if r[1] == 'audio']
    visual_results = [r for r in results if r[1] == 'visual']
    liveness_results = [r for r in results if r[1] == 'liveness']
    
    assert len(audio_results) == 2
    assert len(visual_results) == 2
    assert len(liveness_results) == 2
    
    print(f"\n✓ Thread safety validated: All 6 concurrent tasks completed successfully")


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v', '-s'])
