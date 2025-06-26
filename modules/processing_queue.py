from queue import Queue
from threading import Thread, Lock
import os
import time
from modules.speech_recognizers.speech_recognizer_factory import \
    SpeechRecognizerFactory
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
                "timestamp": time.time()  # Record task adding time
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

                # Get task data
                with self.lock:
                    files = self.results[task_id]["files"]
                    prompt = self.results[task_id]["prompt"]
                    model_size = self.results[task_id].get("model_size")

                # Process each file
                file_results = []
                recognizer = SpeechRecognizerFactory.get_speech_recognizer_by_type(
                    SPEECH_RECOGNIZER_TYPE, model_size)
                llm = LLMProcessor(self.results[task_id].get("llm_model"))

                for i, file_path in enumerate(files):
                    self.results[task_id][
                        "status_info"] = f"There is a total of {len(files)} files, currently processing the {i + 1}th file"
                    # Extract audio (if video)
                    if file_path.lower().endswith(
                            ('.mp4', '.avi', '.mov', '.mkv', '.ts', '.mxf')):
                        audio_path = VideoProcessor.extract_audio(file_path,
                                                                  task_id)
                    else:
                        audio_path = file_path

                    # Speech Recognition
                    print(f"Start speech recognition: {file_path}")
                    result = recognizer.transcribe(audio_path)
                    print(
                        f"Speech recognition completed, number of segments: {len(result['segments'])}")

                    if ENABLE_ALIGNMENT:
                        # Text Alignment
                        print("Start text alignment...")
                        aligner = TextAligner(result['language'])
                        result = aligner.align(result["segments"], audio_path)
                        print(
                            f"Alignment results: {result}")

                    # Calling large model for segmentation
                    print("Calling large model for segmentation...")
                    segments = llm.segment_video(result["segments"], prompt)
                    print(f"The large model is divided into sections: {len(segments)}")

                    # Save the results
                    file_results.append({
                        "filename": os.path.basename(file_path),
                        "align_result": result,
                        "segments": segments,
                        "filepath": file_path
                    })

                # Update results
                with self.lock:
                    self.results[task_id]["status"] = "completed"
                    self.results[task_id]["result"] = file_results

            except Exception as e:
                import traceback
                error_msg = traceback.format_exc()
                print(f"Task processing error: {error_msg}", flush=True)

                with self.lock:
                    self.results[task_id]["status"] = "error"
                    self.results[task_id]["error"] = str(e)
            finally:
                self.queue.task_done()

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
