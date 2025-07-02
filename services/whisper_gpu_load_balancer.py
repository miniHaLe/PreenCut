"""
GPU load balancer for distributing Whisper workload across multiple GPUs.
"""

import threading
import time
import gc
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, Future
from queue import Queue
import os

from core.logging import get_logger
from core.exceptions import SpeechRecognitionError, ConfigurationError
from config.settings import get_settings


def cleanup_whisper_gpu_memory():
    """Simple GPU VRAM cleanup function specifically for Whisper model usage."""
    try:
        # Force garbage collection first
        gc.collect()
        
        # Clear GPU cache if PyTorch is available
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass  # PyTorch not available, skip GPU cleanup
            
    except Exception:
        pass  # Silent cleanup failure


@dataclass
class GPUWorker:
    """Represents a GPU worker for Whisper inference."""
    gpu_id: int
    device_name: str
    is_busy: bool = False
    current_task: Optional[str] = None
    last_used: float = 0.0
    total_jobs: int = 0
    total_time: float = 0.0
    
    @property
    def average_time(self) -> float:
        """Calculate average processing time per job."""
        return self.total_time / self.total_jobs if self.total_jobs > 0 else 0.0


class WhisperGPULoadBalancer:
    """Load balancer for distributing Whisper workload across multiple GPUs."""
    
    def __init__(self, gpu_ids: List[int]):
        self.logger = get_logger(__name__)
        self.settings = get_settings()
        self.gpu_ids = gpu_ids
        self.workers: Dict[int, GPUWorker] = {}
        self.recognizers: Dict[int, Any] = {}
        self.task_queue = Queue()
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=len(gpu_ids))
        
        self._initialize_workers()
        self.logger.info("WhisperGPULoadBalancer initialized", {
            "gpu_ids": gpu_ids,
            "num_workers": len(self.workers)
        })
    
    def _initialize_workers(self) -> None:
        """Initialize GPU workers and their corresponding Whisper models."""
        for gpu_id in self.gpu_ids:
            try:
                # Create worker metadata
                device_name = f"cuda:{gpu_id}"
                worker = GPUWorker(
                    gpu_id=gpu_id,
                    device_name=device_name
                )
                self.workers[gpu_id] = worker
                
                # Initialize Whisper recognizer for this GPU
                self._create_recognizer_for_gpu(gpu_id)
                
                self.logger.info("GPU worker initialized", {
                    "gpu_id": gpu_id,
                    "device_name": device_name
                })
                
            except Exception as e:
                self.logger.error("Failed to initialize GPU worker", {
                    "gpu_id": gpu_id,
                    "error": str(e)
                })
                raise ValueError(f"Failed to initialize GPU {gpu_id}: {str(e)}")
    
    def _create_recognizer_for_gpu(self, gpu_id: int) -> None:
        """Create a Whisper recognizer instance for specific GPU."""
        try:
            recognizer_type = self.settings.speech_recognizer_type
            
            if recognizer_type == "faster_whisper":
                from modules.speech_recognizers.faster_whisper_speech_recognizer import FasterWhisperSpeechRecognizer
                recognizer = FasterWhisperSpeechRecognizer(
                    model_size=self.settings.model.whisper_model_size,
                    device="cuda",
                    device_index=[gpu_id],  # Specific GPU
                    compute_type=self.settings.gpu.whisper_compute_type,
                    batch_size=self.settings.gpu.whisper_batch_size,
                    language=self.settings.model.whisper_language
                )
            elif recognizer_type == "whisperx":
                from modules.speech_recognizers.whisperx_speech_recognizer import WhisperXSpeechRecognizer
                recognizer = WhisperXSpeechRecognizer(
                    model_size=self.settings.model.whisper_model_size,
                    device="cuda",
                    device_index=[gpu_id],  # Specific GPU
                    compute_type=self.settings.gpu.whisper_compute_type,
                    batch_size=self.settings.gpu.whisper_batch_size,
                    language=self.settings.model.whisper_language
                )
            else:
                raise ValueError(f"Unsupported recognizer type: {recognizer_type}")
            
            self.recognizers[gpu_id] = recognizer
            self.logger.info("Whisper recognizer created for GPU", {
                "gpu_id": gpu_id,
                "recognizer_type": recognizer_type,
                "model_size": self.settings.model.whisper_model_size
            })
            
        except Exception as e:
            self.logger.error("Failed to create recognizer for GPU", {
                "gpu_id": gpu_id,
                "error": str(e)
            })
            raise
    
    def get_best_available_gpu(self) -> Optional[int]:
        """Get the best available GPU based on load balancing strategy."""
        with self.lock:
            available_workers = [
                (gpu_id, worker) for gpu_id, worker in self.workers.items() 
                if not worker.is_busy
            ]
            
            if not available_workers:
                return None
            
            # Strategy: Choose GPU with least average processing time
            best_gpu_id = min(available_workers, key=lambda x: x[1].average_time)[0]
            return best_gpu_id
    
    def transcribe_audio(self, audio_path: str, language: str = None) -> Dict[str, Any]:
        """Transcribe audio using the best available GPU."""
        gpu_id = self.get_best_available_gpu()
        
        if gpu_id is None:
            # All GPUs busy, wait for one to become available
            self.logger.warning("All GPUs busy, waiting for availability")
            for _ in range(60):  # Wait up to 60 seconds
                time.sleep(1)
                gpu_id = self.get_best_available_gpu()
                if gpu_id is not None:
                    break
            
            if gpu_id is None:
                raise SpeechRecognitionError("No GPU available for transcription after waiting")
        
        return self._transcribe_on_gpu(gpu_id, audio_path, language)
    
    def _transcribe_on_gpu(self, gpu_id: int, audio_path: str, language: str = None) -> Dict[str, Any]:
        """Perform transcription on specific GPU."""
        worker = self.workers[gpu_id]
        recognizer = self.recognizers[gpu_id]
        
        with self.lock:
            worker.is_busy = True
            worker.current_task = audio_path
            worker.last_used = time.time()
        
        try:
            self.logger.info("Starting transcription on GPU", {
                "gpu_id": gpu_id,
                "audio_path": audio_path,
                "language": language
            })
            
            start_time = time.time()
            
            # Set the GPU context for this transcription
            import torch
            with torch.cuda.device(gpu_id):
                # Update recognizer language if specified
                if language and hasattr(recognizer, 'language'):
                    recognizer.language = language
                elif language:
                    # For recognizers that don't support runtime language change
                    self.logger.warning("Cannot change language at runtime", {
                        "requested_language": language,
                        "gpu_id": gpu_id
                    })
                
                # Perform transcription
                try:
                    result = recognizer.transcribe(audio_path)
                finally:
                    # Clean up GPU memory after model inference on this specific GPU
                    cleanup_whisper_gpu_memory()
            
            processing_time = time.time() - start_time
            
            # Update worker statistics
            with self.lock:
                worker.total_jobs += 1
                worker.total_time += processing_time
            
            self.logger.info("Transcription completed", {
                "gpu_id": gpu_id,
                "processing_time": processing_time,
                "average_time": worker.average_time
            })
            
            return result
            
        except Exception as e:
            self.logger.error("Transcription failed on GPU", {
                "gpu_id": gpu_id,
                "error": str(e)
            })
            raise SpeechRecognitionError(f"Transcription failed on GPU {gpu_id}: {str(e)}")
            
        finally:
            with self.lock:
                worker.is_busy = False
                worker.current_task = None
    
    def transcribe_multiple_files(self, audio_files: List[str], language: str = None) -> List[Dict[str, Any]]:
        """Transcribe multiple audio files in parallel across available GPUs."""
        if not audio_files:
            return []
        
        self.logger.info("Starting parallel transcription", {
            "num_files": len(audio_files),
            "num_gpus": len(self.workers)
        })
        
        futures = []
        results = []
        
        # Submit all transcription tasks
        for audio_path in audio_files:
            future = self.executor.submit(self.transcribe_audio, audio_path, language)
            futures.append((audio_path, future))
        
        # Collect results in order
        for audio_path, future in futures:
            try:
                result = future.result(timeout=600)  # 10 minute timeout per file
                results.append(result)
                
                self.logger.debug("File transcription completed", {
                    "audio_path": audio_path
                })
                
            except Exception as e:
                self.logger.error("File transcription failed", {
                    "audio_path": audio_path,
                    "error": str(e)
                })
                # Add error result to maintain order
                results.append({
                    "error": str(e),
                    "audio_path": audio_path,
                    "segments": []
                })
        
        self.logger.info("Parallel transcription completed", {
            "successful": len([r for r in results if "error" not in r]),
            "failed": len([r for r in results if "error" in r])
        })
        
        return results
    
    def get_gpu_status(self) -> Dict[str, Any]:
        """Get current status of all GPU workers."""
        with self.lock:
            status = {
                "total_gpus": len(self.workers),
                "busy_gpus": len([w for w in self.workers.values() if w.is_busy]),
                "available_gpus": len([w for w in self.workers.values() if not w.is_busy]),
                "workers": {}
            }
            
            for gpu_id, worker in self.workers.items():
                status["workers"][gpu_id] = {
                    "gpu_id": gpu_id,
                    "device_name": worker.device_name,
                    "is_busy": worker.is_busy,
                    "current_task": worker.current_task,
                    "total_jobs": worker.total_jobs,
                    "average_time": worker.average_time,
                    "last_used": worker.last_used
                }
            
            return status
    
    def shutdown(self) -> None:
        """Shutdown the load balancer and clean up resources."""
        self.logger.info("Shutting down GPU load balancer")
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        # Clear recognizers (this should free GPU memory)
        self.recognizers.clear()
        
        self.logger.info("GPU load balancer shutdown complete")


# Global instance
_gpu_load_balancer: Optional[WhisperGPULoadBalancer] = None


def get_whisper_gpu_load_balancer() -> WhisperGPULoadBalancer:
    """Get or create the global Whisper GPU load balancer instance."""
    global _gpu_load_balancer
    
    if _gpu_load_balancer is None:
        settings = get_settings()
        gpu_ids = settings.gpu.whisper_gpu_ids
        
        if not gpu_ids:
            raise ValueError("No GPU IDs configured for Whisper")
        
        _gpu_load_balancer = WhisperGPULoadBalancer(gpu_ids)
    
    return _gpu_load_balancer


def shutdown_whisper_gpu_load_balancer() -> None:
    """Shutdown the global GPU load balancer."""
    global _gpu_load_balancer
    
    if _gpu_load_balancer is not None:
        _gpu_load_balancer.shutdown()
        _gpu_load_balancer = None
