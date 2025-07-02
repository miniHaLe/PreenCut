from queue import Queue
from threading import Thread, Lock
import os
import time
import torch
import gc
from services.speech_recognition_service import SpeechRecognitionService
from modules.text_aligner import TextAligner
from modules.llm_processor import LLMProcessor
from modules.video_processor import VideoProcessor
from config import SPEECH_RECOGNIZER_TYPE, WHISPER_MODEL_SIZE, \
    ENABLE_ALIGNMENT
from typing import List, Dict, Optional


class ProcessingQueue:
    def __init__(self):
        self.queue = Queue()
        self.lock = Lock()
        self.results = {}
        self.result_ttl = 24 * 60 * 60  # Result retention time, in seconds (default 24 hours)
        self.max_results = 100 # Maximum number of results to retain
        self.worker = Thread(target=self._process_queue, daemon=True)
        self.worker.start()
        # Start the cleanup thread
        self.cleanup_worker = Thread(target=self._cleanup_results, daemon=True)
        self.cleanup_worker.start()

    def _clear_gpu_memory(self):
        """Clear GPU VRAM after task completion"""
        try:
            if torch.cuda.is_available():
                # Clear PyTorch GPU cache
                torch.cuda.empty_cache()
                
                # Force garbage collection
                gc.collect()
                
                # Get GPU memory info for logging
                if torch.cuda.device_count() > 0:
                    for i in range(torch.cuda.device_count()):
                        allocated = torch.cuda.memory_allocated(i) / 1024**3  # GB
                        cached = torch.cuda.memory_reserved(i) / 1024**3      # GB
                        print(f"GPU {i} - Allocated: {allocated:.2f}GB, Cached: {cached:.2f}GB")
                
                print("✅ GPU VRAM cleared successfully")
            else:
                print("ℹ️ No GPU available, skipping VRAM cleanup")
        except Exception as e:
            print(f"⚠️ Error clearing GPU memory: {e}")

    def add_task(self, task_id: str, files: List[str], llm_model: str,
                 prompt: Optional[str],
                 whixper_model_size: Optional[str] = None):
        """Adding tasks to the queue"""
        with self.lock:
            self.results[task_id] = {
                "status": "queued",
                "files": files,
                "prompt": prompt,
                "model_size": whixper_model_size,
                "llm_model": llm_model,
                "timestamp": time.time(),  # Record task adding time
                "progress": 0.0,  # Initialize progress at 0%
                "progress_desc": "Đang chờ xử lý"  # Progress description
            }
        self.queue.put(task_id)

    def get_queue_size(self) -> int:
        """Get the number of tasks in the queue (excluding those currently being executed)"""
        return self.queue.qsize()

    def _process_queue(self):
        """Processing tasks in the queue"""
        while True:
            task_id = self.queue.get()
            try:
                with self.lock:
                    self.results[task_id]["status"] = "processing"
                    self.results[task_id]["progress"] = 0.01
                    self.results[task_id]["progress_desc"] = "Bắt đầu xử lý"

                # Get task data
                with self.lock:
                    files = self.results[task_id]["files"]
                    prompt = self.results[task_id]["prompt"]
                    model_size = self.results[task_id].get("model_size")

                # Process each file
                file_results = []
                speech_service = SpeechRecognitionService(recognizer_type=SPEECH_RECOGNIZER_TYPE)
                llm = LLMProcessor(self.results[task_id].get("llm_model"))

                total_files = len(files)
                for i, file_path in enumerate(files):
                    # Update progress for this file
                    file_progress_base = i / total_files
                    file_progress_weight = 1 / total_files
                    
                    with self.lock:
                        self.results[task_id]["status_info"] = f"Đang xử lý tệp {i + 1}/{total_files}"
                        self.results[task_id]["progress"] = file_progress_base
                        self.results[task_id]["progress_desc"] = f"Đang xử lý tệp {i + 1}/{total_files}"
                    
                    # Extract audio (if video)
                    if file_path.lower().endswith(
                            ('.mp4', '.avi', '.mov', '.mkv', '.ts', '.mxf')):
                        with self.lock:
                            self.results[task_id]["progress"] = file_progress_base + file_progress_weight * 0.1
                            self.results[task_id]["progress_desc"] = f"Đang trích xuất âm thanh từ tệp {i + 1}/{total_files}"
                        audio_path = VideoProcessor.extract_audio(file_path,
                                                                  task_id)
                    else:
                        audio_path = file_path

                    # Speech Recognition
                    print(f"Start speech recognition: {file_path}")
                    with self.lock:
                        self.results[task_id]["progress"] = file_progress_base + file_progress_weight * 0.2
                        self.results[task_id]["progress_desc"] = f"Đang nhận dạng giọng nói từ video {i + 1}/{total_files}"
                    result = speech_service.transcribe_audio(audio_path)
                    print(
                        f"Speech recognition completed, number of segments: {len(result['segments'])}")

                    if ENABLE_ALIGNMENT:
                        # Text Alignment
                        print("Start text alignment...")
                        with self.lock:
                            self.results[task_id]["progress"] = file_progress_base + file_progress_weight * 0.6
                            self.results[task_id]["progress_desc"] = f"Đang căn chỉnh và phân tích video {i + 1}/{total_files}"
                        aligner = TextAligner(result['language'])
                        result = aligner.align(result["segments"], audio_path)
                        print(
                            f"Alignment results: {result}")

                    # Calling large model for segmentation
                    print("Calling large model for segmentation...")
                    with self.lock:
                        self.results[task_id]["progress"] = file_progress_base + file_progress_weight * 0.8
                        self.results[task_id]["progress_desc"] = f"Đang phân đoạn và tóm tắt video {i + 1}/{total_files}"
                    segments = llm.segment_video(result["segments"], prompt)
                    print(f"The large model is divided into sections: {len(segments)}")

                    # Save the results
                    file_results.append({
                        "filename": os.path.basename(file_path),
                        "align_result": result,
                        "segments": segments,
                        "filepath": file_path
                    })
                    
                    # Update completion of this file
                    with self.lock:
                        self.results[task_id]["progress"] = file_progress_base + file_progress_weight
                        self.results[task_id]["progress_desc"] = f"Đã hoàn thành phân tích video {i + 1}/{total_files}"

                # Update results
                with self.lock:
                    self.results[task_id]["status"] = "completed"
                    self.results[task_id]["result"] = file_results
                    self.results[task_id]["progress"] = 1.0
                    self.results[task_id]["progress_desc"] = "Xử lý hoàn tất"

                print(f"✅ Task {task_id} completed successfully")

            except Exception as e:
                import traceback
                error_msg = traceback.format_exc()
                print(f"Task processing error: {error_msg}", flush=True)

                with self.lock:
                    self.results[task_id]["status"] = "error"
                    self.results[task_id]["error"] = str(e)
                    self.results[task_id]["progress"] = 0.0
                    self.results[task_id]["progress_desc"] = f"Lỗi: {str(e)}"
                
                print(f"❌ Task {task_id} failed with error: {str(e)}")
            
            finally:
                # Always clear GPU memory after task completion (success or failure)
                self._clear_gpu_memory()
                self.queue.task_done()
                print(f"🧹 Task {task_id} cleanup completed")

    def get_result(self, task_id: str) -> Dict:
        """Get task results"""
        with self.lock:
            result = self.results.get(task_id, {"status": "not_found"})
            if result["status"] != "not_found":
                # Update access time to avoid being cleaned up
                result["last_accessed"] = time.time()
            return result

    def _cleanup_results(self):
        """Regularly clean up expired or excessive results"""
        while True:
            time.sleep(1 * 60 * 60)  # 每1小时清理一次
            with self.lock:
                current_time = time.time()
                # Results list sorted by time
                sorted_results = sorted(
                    self.results.items(),
                    key=lambda x: x[1].get("last_accessed", x[1]["timestamp"])
                )

                # Remove expired results
                for task_id, result in list(sorted_results):
                    age = current_time - result.get("last_accessed",
                                                    result["timestamp"])
                    if age > self.result_ttl:
                        self.results.pop(task_id, None)

                # Limit the maximum number of results
                if len(self.results) > self.max_results:
                    # Delete the oldest results
                    to_remove = len(self.results) - self.max_results
                    for task_id, _ in sorted_results[:to_remove]:
                        self.results.pop(task_id, None)
