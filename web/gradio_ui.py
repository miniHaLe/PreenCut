import os
import uuid
import time
import random
import zipfile
import traceback
import torch
import gc
import gradio as gr
from config import LLM_MODEL_OPTIONS

from config import (
    TEMP_FOLDER,
    OUTPUT_FOLDER,
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE,
    SPEECH_RECOGNIZER_TYPE,
    WHISPER_MODEL_SIZE,
    MAX_FILE_NUMBERS,
    ENABLE_ALIGNMENT
)
from modules.processing_queue import ProcessingQueue
from modules.video_processor import VideoProcessor
from modules.llm_processor import LLMProcessor
from utils.time_utils import seconds_to_hhmmss, hhmmss_to_seconds
from utils.file_utils import clear_directory_fast, generate_safe_filename
from typing import List, Dict, Tuple, Optional, Any, Union
import subprocess

# Global instance
processing_queue = ProcessingQueue()
CHECKBOX_CHECKED = '<span style="display: flex; width: 16px; height: 16px; border: 2px solid blue; background:#4B6BFB ;font-weight: bold;color:white;align-items:center;justify-content:center">✓</span>'
CHECKBOX_UNCHECKED = '<span style="display: flex; width: 16px; height: 16px; border: 2px solid blue;font-weight: bold;color:white;align-items:center;justify-content:center"></span>'

# Global storage for transcription summaries (replaces chapter summaries)
transcription_summaries_cache = {}


def format_transcription_summary_markdown(summary_data: Dict) -> str:
    """Format transcription summary data as clean Markdown for Gradio"""
    if not summary_data:
        return """
## ⚠️ Không có tóm tắt nào được tạo

Hệ thống không thể tạo tóm tắt cho nội dung này.
        """
    
    summary = summary_data.get('summary', 'Không có tóm tắt')
    highlights = summary_data.get('highlights', [])
    key_insights = summary_data.get('key_insights', [])
    conclusion = summary_data.get('conclusion', 'Không có kết luận')
    
    # Build markdown content
    markdown_content = f"""
# 📋 Tóm tắt nội dung transcription

## 📄 Tóm tắt chính
{summary}

"""
    
    # Add highlights if available
    if highlights and isinstance(highlights, list) and len(highlights) > 0:
        markdown_content += "## ✨ Điểm nổi bật\n"
        for highlight in highlights:
            if highlight and highlight.strip():
                markdown_content += f"- {highlight}\n"
        markdown_content += "\n"
    
    # Add key insights if available
    if key_insights and isinstance(key_insights, list) and len(key_insights) > 0:
        markdown_content += "## 🔑 Những hiểu biết chính\n"
        for insight in key_insights:
            if insight and insight.strip():
                markdown_content += f"- {insight}\n"
        markdown_content += "\n"
    
    # Add conclusion
    markdown_content += f"""## 🎯 Kết luận
{conclusion}

---
**💡 Ghi chú:** Tóm tắt này được tạo tự động bằng AI từ toàn bộ nội dung video. 
Để hiểu rõ và đầy đủ nhất, hãy tham khảo cùng với video gốc.
"""
    
    return markdown_content


def normalize_relevancy_score(score) -> float:
    """Normalize relevancy score to 1-10 scale from various input ranges"""
    if score is None:
        return 5.0  # Default neutral score
    
    try:
        score_float = float(score)
        
        # If score is 0, always maps to 1.0
        if score_float == 0.0:
            return 1.0
        
        # If score is in 0.01-0.99 range (clearly decimal), scale to 1-10
        elif 0.01 <= score_float <= 0.99:
            normalized = score_float * 9.0 + 1.0
            return round(normalized, 1)
        
        # If score is exactly 1.0, assume it's max of 0-1 range -> 10.0
        elif score_float == 1.0:
            return 10.0
        
        # If score is in 1.01-10.0 range, it's already in target range
        elif 1.01 <= score_float <= 10.0:
            return round(score_float, 1)
        
        # If score is in 10.01-100 range, scale from 0-100 to 1-10
        elif 10.01 <= score_float <= 100.0:
            normalized = (score_float / 100.0) * 9.0 + 1.0
            return round(normalized, 1)
        
        # If score is negative, clamp to 1.0
        elif score_float < 0:
            return 1.0
        
        # If score is > 100, clamp to 10.0
        else:
            return 10.0
            
    except (ValueError, TypeError):
        print(f"Warning: Could not parse relevancy score '{score}', using default 5.0")
        return 5.0


def format_transcription_summary_html(summary_data: Dict) -> str:
    """Legacy HTML formatter - deprecated, use format_transcription_summary_markdown instead"""
    # Keep for backward compatibility but redirect to markdown version
    return format_transcription_summary_markdown(summary_data)


def get_transcription_summary_for_task(task_id: str) -> str:
    """Get formatted transcription summary Markdown for a task"""
    try:
        print(f"[DEBUG] Getting transcription summary for task: {task_id}")
        
        # Get the processing result
        result = processing_queue.get_result(task_id)
        print(f"[DEBUG] Task status: {result.get('status')}")
        
        if result["status"] != "completed":
            return """
## ⏳ Đang xử lý

Vui lòng hoàn thành xử lý video trước khi xem tóm tắt.
            """
        
        # Get transcription summary from results
        summary_data = result.get("transcription_summary")
        print(f"[DEBUG] Summary data available: {summary_data is not None}")
        
        if not summary_data:
            return """
## ⚠️ Không có tóm tắt

Tóm tắt có thể chưa được tạo hoặc gặp lỗi trong quá trình xử lý.
            """
        
        formatted_summary = format_transcription_summary_markdown(summary_data)
        print(f"[DEBUG] Formatted summary length: {len(formatted_summary)}")
        return formatted_summary
        
    except Exception as e:
        print(f"Lỗi lấy tóm tắt transcription: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"""
## ❌ Lỗi hiển thị tóm tắt

{str(e)}
        """


def check_uploaded_files(files: List) -> str:
    """Check if the uploaded file meets the requirements"""
    if not files:
        raise gr.Error("Vui lòng tải lên ít nhất một tệp")

    if len(files) > MAX_FILE_NUMBERS:
        raise gr.Error(
            f"Số lượng tệp tải lên vượt quá giới hạn ({len(files)} > {MAX_FILE_NUMBERS})")

    saved_paths = []
    for file in files:
        filename = os.path.basename(file.name)

        # Check the file size
        file_size = os.path.getsize(file.name)
        if file_size > MAX_FILE_SIZE:
            raise gr.Error(f"Kích thước tệp vượt quá giới hạn ({file_size} > {MAX_FILE_SIZE})")

        # Check the file format
        ext = os.path.splitext(filename)[1].lower()  # Keep the dot
        if ext not in ALLOWED_EXTENSIONS:
            raise gr.Error(
                f"Định dạng tệp không được hỗ trợ: {ext}, Chỉ hỗ trợ: {', '.join(ALLOWED_EXTENSIONS)}")

        saved_paths.append(file.name)

    return saved_paths


def update_processing_status(task_id: str, progress: float, desc: str):
    """Update processing status in the queue for display in status column"""
    with processing_queue.lock:
        if task_id in processing_queue.results:
            processing_queue.results[task_id].update({
                "progress": progress,
                "progress_desc": desc,
                "timestamp": time.time()
            })


def clear_gpu_memory():
    """Clear GPU VRAM after processing"""
    try:
        if torch.cuda.is_available():
            # Clear PyTorch GPU cache
            torch.cuda.empty_cache()
            
            # Force garbage collection
            gc.collect()
            
            print("✅ GPU VRAM cleared successfully")
        else:
            print("ℹ️ No GPU available, skipping VRAM cleanup")
    except Exception as e:
        print(f"⚠️ Error clearing GPU memory: {e}")


def process_files_with_progress(files: List, progress=gr.Progress(track_tqdm=True)) -> Tuple[str, Dict]:
    """Processing uploaded files with progress bar updates"""
    
    print(f"[DEBUG] process_files_with_progress called with {len(files) if files else 0} files")
    print(f"[DEBUG] Progress object type: {type(progress)}")
    
    # Use default values for removed UI components
    llm_model = LLM_MODEL_OPTIONS[0]['label'] if LLM_MODEL_OPTIONS else "llama3.1"
    prompt = None  # No prompt needed as per user request
    whisper_model_size = WHISPER_MODEL_SIZE  # Use default from config
    
    # Initialize progress tracking
    try:
        print("[DEBUG] Calling progress(0, desc='Đang khởi tạo...')")
        progress(0, desc="Đang khởi tạo...")
        print("[DEBUG] Progress call successful")
    except Exception as e:
        print(f"[DEBUG] Progress call failed: {e}")
    
    # Check whether the uploaded files meet the requirements
    saved_paths = check_uploaded_files(files)
    
    # Create a unique task ID
    task_id = f"task_{uuid.uuid4().hex}"
    
    print(f"Bắt đầu xử lý: {task_id}, Đường dẫn tệp: {saved_paths}", flush=True)

    # Initialize status in processing queue
    with processing_queue.lock:
        processing_queue.results[task_id] = {
            "status": "processing",
            "progress": 0.05,
            "progress_desc": "Khởi tạo tác vụ...",
            "timestamp": time.time()
        }
    
    # Return immediate status for UI updates
    initial_status = {
        "task_id": task_id,
        "status": "Đang xử lý...",
        "progress": 0.05,
        "progress_desc": "Khởi tạo tác vụ..."
    }

    # Process files directly with progress
    from modules.llm_processor import LLMProcessor
    from modules.video_processor import VideoProcessor
    from config import SPEECH_RECOGNIZER_TYPE, ENABLE_ALIGNMENT
    from services.speech_recognition_service import SpeechRecognitionService
    
    progress(0.05, desc="Khởi tạo các mô hình...")
    update_processing_status(task_id, 0.05, "Khởi tạo các mô hình...")
    
    try:
        # Initialize models with new service
        speech_service = SpeechRecognitionService(recognizer_type=SPEECH_RECOGNIZER_TYPE)
        llm = LLMProcessor(llm_model)
        
        progress(0.1, desc="Đã khởi tạo các mô hình")
        update_processing_status(task_id, 0.1, "Đã khởi tạo các mô hình")
        
        # Process each file with tqdm progress bars for better UX
        file_results = []
        total_files = len(saved_paths)
        
        # Use tqdm progress bar for file processing
        for i, file_path in enumerate(progress.tqdm(saved_paths, desc="Processing files")):
            print(f"Processing file {i+1}/{total_files}: {os.path.basename(file_path)}")
            
            # Extract audio (if video)
            if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.ts', '.mxf')):
                progress(0.2 + (i * 0.8 / total_files), desc=f"Extracting information from {os.path.basename(file_path)}")
                update_processing_status(task_id, 0.2 + (i * 0.8 / total_files), f"Trích xuất thông tin từ {os.path.basename(file_path)}")
                audio_path = VideoProcessor.extract_audio(file_path, task_id)
            else:
                audio_path = file_path

            # Speech Recognition
            progress(0.3 + (i * 0.8 / total_files), desc=f"Speech recognition: {os.path.basename(file_path)}")
            update_processing_status(task_id, 0.3 + (i * 0.8 / total_files), f"Nhận dạng giọng nói: {os.path.basename(file_path)}")
            
            print(f"Bắt đầu nhận dạng giọng nói: {file_path}")
            result = speech_service.transcribe_audio(audio_path)
            print(f"Hoàn thành nhận dạng giọng nói, số phân đoạn: {len(result['segments'])}")

            # Text Alignment (if enabled) with tqdm for segments
            if ENABLE_ALIGNMENT:
                progress(0.5 + (i * 0.8 / total_files), desc=f"Video alignment: {os.path.basename(file_path)}")
                update_processing_status(task_id, 0.5 + (i * 0.8 / total_files), f"Căn chỉnh video: {os.path.basename(file_path)}")
                try:
                    from modules.text_aligner import TextAligner
                    aligner = TextAligner(result['language'])
                    aligned_result = aligner.align(result["segments"], audio_path)
                    
                    # Check if alignment was successful
                    if aligned_result.get("alignment_failed", False):
                        print(f"⚠️ Alignment failed for {file_path}, using original segments")
                        print(f"Alignment error: {aligned_result.get('alignment_error', 'Unknown error')}")
                        # Keep original result, don't replace with failed alignment
                    else:
                        print(f"✅ Alignment successful for {file_path}")
                        result = aligned_result
                        
                except Exception as e:
                    print(f"❌ Alignment module error for {file_path}: {str(e)}")
                    print("Continuing with original segments without alignment")
                    # Continue with original result

            # LLM Processing
            progress(0.7 + (i * 0.8 / total_files), desc=f"AI analysis: {os.path.basename(file_path)}")
            update_processing_status(task_id, 0.7 + (i * 0.8 / total_files), f"Phân tích và tóm tắt: {os.path.basename(file_path)}")
            
            print("Gọi mô hình ngôn ngữ lớn để phân đoạn...")
            
            # Use actual subtitle segments for accurate timestamps
            segments = llm.segment_video_with_timestamps(result["segments"], prompt)
            print(f"Mô hình ngôn ngữ lớn đã phân chia thành: {len(segments)} phân đoạn")

            # Save results
            file_results.append({
                "filename": os.path.basename(file_path),
                "align_result": result,
                "segments": segments,
                "filepath": file_path
            })
            
            # Update progress for completed file
            progress(0.8 + ((i + 1) * 0.1 / total_files), desc=f"Completed file {i + 1}/{total_files}")
            update_processing_status(task_id, 0.8 + ((i + 1) * 0.1 / total_files), f"Hoàn thành tệp {i + 1}/{total_files}")
        
        # Final preparation steps with tqdm
        progress(0.9, desc="Preparing results display...")
        update_processing_status(task_id, 0.9, "Chuẩn bị kết quả hiển thị...")
        
        # Prepare results for display
        display_result = []
        clip_result = []
        full_transcript = ""
        
        # Create a directory for thumbnails
        thumbnail_dir = os.path.join(TEMP_FOLDER, "thumbnails", task_id)
        os.makedirs(thumbnail_dir, exist_ok=True)
        
        # Process results with tqdm progress for better UX
        for file_result in progress.tqdm(file_results, desc="Building transcripts and thumbnails"):
            # Build transcript from original speech recognition results
            align_result = file_result.get("align_result", {})
            if "segments" in align_result:
                for seg in align_result["segments"]:
                    text = seg.get("text", "").strip()
                    if text:
                        start_time = seg.get("start", 0)
                        full_transcript += f"[{seconds_to_hhmmss(start_time)}] {text}\n"
            
            # Process segments with tqdm for thumbnail generation
            for seg in progress.tqdm(file_result["segments"], desc=f"Processing segments for {file_result['filename']}"):
                # Generate thumbnail at the middle of the segment
                thumbnail_path = ""
                try:
                    video_path = file_result["filepath"]
                    thumbnail_time = (seg['start'] + seg['end']) / 2
                    thumbnail_filename = f"{file_result['filename']}_{seg['start']:.1f}_{seg['end']:.1f}.jpg"
                    thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
                    
                    if not os.path.exists(thumbnail_path):
                        VideoProcessor.extract_thumbnail(video_path, thumbnail_time, thumbnail_path)
                except Exception as e:
                    print(f"Lỗi tạo thumbnail: {str(e)}")
                
                # Create row for clipping options table
                # Create better relevance score display with normalization
                relevance_score = seg.get('relevance_score')
                if relevance_score is not None:
                    normalized_score = normalize_relevancy_score(relevance_score)
                    relevance_display = f"{normalized_score:.1f}/10"
                else:
                    relevance_display = "N/A"
                    print(f"[WARNING] Missing relevance_score in regular results for segment: {seg.get('summary', 'Unknown')}")
                
                clip_row = [
                    CHECKBOX_UNCHECKED,
                    file_result["filename"],
                    f"{seconds_to_hhmmss(seg['start'])}",
                    f"{seconds_to_hhmmss(seg['end'])}",
                    f"{seconds_to_hhmmss(seg['end'] - seg['start'])}",
                    seg["summary"],
                    ", ".join(seg["tags"]) if isinstance(seg["tags"], list) else seg["tags"],
                    relevance_display  # Relevance score
                ]
                clip_result.append(clip_row)
        
        # Generate transcription summary automatically with progress feedback
        progress(0.95, desc="Generating transcription summary...")
        update_processing_status(task_id, 0.95, "Tạo tóm tắt transcription...")
        transcription_summary = None
        try:
            if full_transcript.strip():
                # Show progress for summary generation
                for step in progress.tqdm(["Analyzing transcript", "Generating summary", "Formatting output"], desc="Creating summary"):
                    if step == "Analyzing transcript":
                        time.sleep(0.1)  # Brief pause for visual feedback
                    elif step == "Generating summary":
                        transcription_summary = llm.generate_transcription_summary(full_transcript)
                    elif step == "Formatting output":
                        time.sleep(0.1)  # Brief pause for visual feedback
                
                print(f"Tạo tóm tắt transcription thành công: {len(transcription_summary.get('summary', ''))} ký tự")
            else:
                print("Transcript trống, bỏ qua tạo tóm tắt")
        except Exception as e:
            print(f"Lỗi tạo tóm tắt transcription: {str(e)}")
            import traceback
            traceback.print_exc()
            transcription_summary = None
        
        # Store results in the processing queue for later access
        with processing_queue.lock:
            processing_queue.results[task_id] = {
                "status": "completed",
                "result": file_results,
                "transcription_summary": transcription_summary,
                "timestamp": time.time(),
                "progress": 1.0,
                "progress_desc": "Xử lý hoàn tất"
            }
        
        final_desc = "Hoàn tất xử lý!"
        progress(1.0, desc=final_desc)
        update_processing_status(task_id, 1.0, final_desc)
        
        # Clear GPU memory after successful processing
        clear_gpu_memory()
        
        return (task_id, 
                {"task_id": task_id, "status": "Xử lý hoàn tất",
                 "raw_result": file_results, "result": clip_result,
                 "progress": 1.0, "progress_desc": "Xử lý hoàn tất"})
        
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"Lỗi xử lý tác vụ: {error_msg}", flush=True)
        
        # Store error in processing queue
        with processing_queue.lock:
            processing_queue.results[task_id] = {
                "status": "error",
                "error": str(e),
                "timestamp": time.time(),
                "progress": 0.0,
                "progress_desc": f"Lỗi: {str(e)}"
            }
        
        # Clear GPU memory even after error
        clear_gpu_memory()
        
        raise gr.Error(f"Lỗi xử lý: {str(e)}")


def process_files(files: List,
                  progress=gr.Progress()) -> Tuple[str, Dict]:
    """Processing uploaded files (legacy function for compatibility)"""
    
    # Use default values for removed UI components
    llm_model = LLM_MODEL_OPTIONS[0]['label'] if LLM_MODEL_OPTIONS else "llama3.1"
    prompt = None  # No prompt needed as per user request
    whisper_model_size = WHISPER_MODEL_SIZE  # Use default from config

    # Check whether the uploaded files meet the requirements
    saved_paths = check_uploaded_files(files)
    
    # Create a unique task ID
    task_id = f"task_{uuid.uuid4().hex}"
    
    # Initialize status in processing queue
    with processing_queue.lock:
        processing_queue.results[task_id] = {
            "status": "processing",
            "progress": 0.05,
            "progress_desc": "Khởi tạo tác vụ...",
            "timestamp": time.time()
        }

    print(f"Thêm tác vụ: {task_id}, Đường dẫn tệp: {saved_paths}", flush=True)

    # Add to the processing queue
    processing_queue.add_task(task_id, saved_paths, llm_model, prompt,
                              whisper_model_size)
    
    update_processing_status(task_id, 0.1, "Đã thêm vào hàng đợi, đang xử lý...")

    return task_id, {"status": "Đã tham gia hàng đợi, vui lòng đợi...",
                     "progress_desc": "Đã thêm vào hàng đợi, đang xử lý...",
                     "progress": 0.1}


def check_status(task_id: str, current_selection: List[List] = None) -> Tuple[Dict, List, List]:
    """Checking the Task Status"""
    result = processing_queue.get_result(task_id)

    # Preserve current selection state if provided
    selection_state = {}
    if current_selection:
        for row in current_selection:
            if len(row) >= 4:  # Ensure we have enough columns
                # Use filename + start + end as unique identifier for each clip
                key = f"{row[1]}_{row[2]}_{row[3]}"
                selection_state[key] = row[0] == CHECKBOX_CHECKED

    if result["status"] == "completed":
        # Arrange results for display
        display_result = []
        clip_result = []
        
        # Create a directory for thumbnails if it doesn't exist
        thumbnail_dir = os.path.join(TEMP_FOLDER, "thumbnails", task_id)
        os.makedirs(thumbnail_dir, exist_ok=True)
        
        for file_result in result["result"]:
            for seg in file_result["segments"]:
                # Generate thumbnail at the middle of the segment
                thumbnail_path = ""
                try:
                    video_path = file_result["filepath"]
                    thumbnail_time = (seg['start'] + seg['end']) / 2  # Middle of segment
                    thumbnail_filename = f"{file_result['filename']}_{seg['start']:.1f}_{seg['end']:.1f}.jpg"
                    thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
                    
                    # Only generate thumbnail if it doesn't exist
                    if not os.path.exists(thumbnail_path):
                        print(f"Generating thumbnail: {thumbnail_path}")
                        generated_path = VideoProcessor.extract_thumbnail(video_path, thumbnail_time, thumbnail_path)
                        if generated_path and os.path.exists(generated_path):
                            thumbnail_path = generated_path
                            print(f"Thumbnail generated successfully: {thumbnail_path}")
                        else:
                            print(f"Failed to generate thumbnail: {thumbnail_path}")
                            thumbnail_path = ""
                    else:
                        print(f"Thumbnail already exists: {thumbnail_path}")
                except Exception as e:
                    print(f"Error generating thumbnail: {str(e)}")
                    thumbnail_path = ""
                
                # Create row for analysis results table
                row = [file_result["filename"],
                       f"{seconds_to_hhmmss(seg['start'])}",
                       f"{seconds_to_hhmmss(seg['end'])}",
                       f"{seconds_to_hhmmss(seg['end'] - seg['start'])}",
                       seg["summary"],
                       ", ".join(seg["tags"]) if isinstance(
                           seg["tags"], list) else seg["tags"],
                       thumbnail_path]  # Add thumbnail path
                display_result.append(row)
                
                # Create row for clipping options table - ensure correct column order with checkbox
                key = f"{file_result['filename']}_{seconds_to_hhmmss(seg['start'])}_{seconds_to_hhmmss(seg['end'])}"
                checkbox_state = CHECKBOX_CHECKED if selection_state.get(key, False) else CHECKBOX_UNCHECKED
                
                # Get enhanced fields with defaults
                word_count = seg.get('word_count', len(seg.get('summary', '').split()))
                relevance_score = seg.get('relevance_score', seg.get('relevance', 5))  # fallback compatibility
                engagement_score = seg.get('engagement_score', 5)
                composite_score = seg.get('composite_score', relevance_score * 0.6 + engagement_score * 0.4)
                
                # Format scores for display with normalization
                if isinstance(relevance_score, (int, float)):
                    normalized_score = normalize_relevancy_score(relevance_score)
                    relevance_display = f"{normalized_score:.1f}/10"
                else:
                    relevance_display = "5.0/10"
                
                clip_row = [
                    checkbox_state,  # Checkbox column - preserve state
                    file_result["filename"],  # Filename column
                    f"{seconds_to_hhmmss(seg['start'])}",  # Start time
                    f"{seconds_to_hhmmss(seg['end'])}",  # End time
                    f"{seconds_to_hhmmss(seg['end'] - seg['start'])}",  # Duration
                    seg["summary"],  # Summary
                    ", ".join(seg["tags"]) if isinstance(seg["tags"], list) else seg["tags"],  # Tags
                    relevance_display  # Relevance score
                ]
                clip_result.append(clip_row)

        return (
            {"task_id": task_id, "status": "Xử lý hoàn tất",
             "raw_result": result["result"],
             "result": display_result,
             "progress": 1.0,
             "progress_desc": "Xử lý hoàn tất"},
            display_result,
            clip_result
        )

    elif result["status"] == "error":
        return (
            {"task_id": task_id,
             "status": f"Lỗi: {result.get('error', 'Lỗi không xác định')}",
             "progress": 0.0,
             "progress_desc": f"Lỗi: {result.get('error', 'Lỗi không xác định')}"},
            [], []
        )
    elif result["status"] == "queued":
        return (
            {"task_id": task_id,
             "status": f"Trong hàng đợi, còn {processing_queue.get_queue_size()} tác vụ",
             "progress": 0.0,
             "progress_desc": f"Trong hàng đợi, còn {processing_queue.get_queue_size()} tác vụ"},
            [], []
        )

    if task_id:
        # Get progress information
        progress = result.get("progress", 0.0)
        progress_desc = result.get("progress_desc", "Đang xử lý...")
        
        return (
            {"task_id": task_id, 
             "status": "Đang xử lý...",
             "status_info": result.get("status_info", ""),
             "progress": progress,
             "progress_desc": progress_desc},
            [], []
        )
    else:
        return (
            {"task_id": "", 
             "status": "",
             "progress": 0.0,
             "progress_desc": ""},
            [], []
        )


def select_clip(segment_selection: List[List], evt: gr.SelectData) -> List[
    List]:
    """Chọn phân đoạn"""
    selected_row = segment_selection[evt.index[0]]
    # Toggle selection state for checkbox column (index 0)
    selected_row[0] = CHECKBOX_CHECKED \
        if selected_row[0] == CHECKBOX_UNCHECKED else CHECKBOX_UNCHECKED
    return segment_selection


def clip_and_download(status_display: Dict,
                      segment_selection: List[List], download_mode: str) -> str:
    """Clip and download selected clips"""
    if not status_display or "raw_result" not in status_display:
        raise gr.Error("Kết quả xử lý không hợp lệ")

    # Get the task ID to create a unique directory
    task_id = status_display.get("task_id",
                                 f"temp_{int(time.time() * 1000)}_{random.randint(1000, 9999)}")
    task_temp_dir = os.path.join(TEMP_FOLDER, task_id)
    task_output_dir = os.path.join(OUTPUT_FOLDER, task_id)

    if os.path.exists(task_output_dir):
        clear_directory_fast(task_output_dir)
    else:
        os.makedirs(task_output_dir, exist_ok=True)
    if os.path.exists(task_temp_dir):
        clear_directory_fast(task_temp_dir)
    else:
        os.makedirs(task_temp_dir, exist_ok=True)

    # Organize files into segments
    file_segments = {}
    for file_data in status_display["raw_result"]:
        file_segments[file_data["filename"]] = {
            "segments": file_data["segments"],
            "filepath": file_data["filepath"],
            "ext": os.path.splitext(file_data["filepath"])[1]  # Get the original file extension
        }

    selected_segments = [seg for seg in segment_selection if
                         seg[0] == CHECKBOX_CHECKED]

    # Handling the "merge into one file" situation
    if download_mode == "Ghép thành một tệp":
        # Check that all fragment formats are consistent
        formats = set()
        for seg in selected_segments:
            # Column 1 is now the filename (0 is checkbox)
            filename = seg[1]
            file_ext = file_segments[filename]['ext']
            formats.add(file_ext.lower())

        if len(formats) > 1:
            raise gr.Error(
                "Không thể ghép: Các đoạn được chọn chứa nhiều định dạng khác nhau: " + ", ".join(formats))

    selected_clips = []
    for seg in selected_segments:
        # Update column indices: 1=filename, 2=start, 3=end
        filename = seg[1]
        start = hhmmss_to_seconds(seg[2])
        end = hhmmss_to_seconds(seg[3])

        # Find the corresponding original segment
        for original_seg in file_segments[filename]['segments']:
            if abs(original_seg["start"] - start) < 0.5 and abs(
                    original_seg["end"] - end) < 0.5:
                selected_clips.append({
                    "filename": filename,
                    "start": original_seg["start"],
                    "end": original_seg["end"],
                    "filepath": file_segments[filename]['filepath'],
                    "ext": file_segments[filename]['ext']  # Add extension
                })
                break

    # Group by file
    clips_by_file = {}
    for clip in selected_clips:
        if clip["filename"] not in clips_by_file:
            clips_by_file[clip["filename"]] = {
                "filepath": clip["filepath"],
                "ext": clip["ext"],
                "segments": []
            }
        clips_by_file[clip["filename"]]['segments'].append({
            "start": clip["start"],
            "end": clip["end"],
        })

    # Process each file
    output_files = []
    for filename, segments in clips_by_file.items():
        input_path = segments['filepath']
        # Generate safe directory names (a file may have multiple fragments, which are placed in a directory named after the file name)
        safe_filename = generate_safe_filename(filename)
        output_folder = os.path.join(task_output_dir, safe_filename)
        os.makedirs(output_folder, exist_ok=True)
        single_file_clips = VideoProcessor.clip_video(input_path,
                                                      segments['segments'],
                                                      output_folder,
                                                      segments['ext'])
        output_files.extend(single_file_clips)

    # If there is only one file, return directly
    if len(output_files) == 1:
        return output_files[0]

    # Process according to the mode selected by the user
    if download_mode == "Ghép thành một tệp":
        # Merge multiple files
        ext = clips_by_file[next(iter(clips_by_file))]['ext']  # Get the extension of the first file
        combined_path = os.path.join(task_output_dir, f"combined_output{ext}")

        # Create a file list
        with open(os.path.join(task_temp_dir, "combine_list.txt"), 'w') as f:
            for file in output_files:
                f.write(f"file '../../{file}'\n")

        # Merge Videos
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', os.path.join(task_temp_dir, "combine_list.txt"),
            '-c', 'copy', combined_path
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Lỗi FFmpeg: {e.stderr.decode('utf-8')}")
            raise gr.Error(f"Ghép tệp thất bại: {str(e)}")

        return combined_path

    # Package into zip file
    else:
        # Create zip file
        zip_path = os.path.join(task_output_dir, "clipped_segments.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for file_path in output_files:
                # Using relative paths in zip files
                arcname = os.path.basename(file_path)
                zipf.write(file_path, arcname)

        return zip_path


def start_reanalyze() -> Dict:
    return {
        'status': 'Vui lòng đợi, đang phân tích lại với gợi ý mới...',
    }


def reanalyze_with_prompt(task_id: str,
                          new_prompt: str,
                          progress=gr.Progress()) -> Tuple[Dict, List[List]]:
    """Reanalysis with specific prompt"""
    # Use default LLM model
    reanalyze_llm_model = LLM_MODEL_OPTIONS[0]['label'] if LLM_MODEL_OPTIONS else "llama3.1"
    if not task_id:
        raise gr.Error("Không có tác vụ xử lý nào đang hoạt động")

    if not new_prompt:
        raise gr.Error("Vui lòng nhập chủ đề cần trích xuất")

    # Get current results
    result = processing_queue.get_result(task_id)
    if result["status"] != "completed":
        raise gr.Error("Tác vụ chưa hoàn thành, vui lòng đợi")

    update_processing_status(task_id, 0.1, "Đang khởi tạo phân tích mới...")
    
    # Create a directory for thumbnails if it doesn't exist
    thumbnail_dir = os.path.join(TEMP_FOLDER, "thumbnails", task_id)
    os.makedirs(thumbnail_dir, exist_ok=True)
    
    # Get raw data for reanalysis
    file_results = []
    
    for i, file_result in enumerate(result["result"]):
        update_processing_status(task_id, 0.1 + (i / len(result["result"]) * 0.6), 
                f"Đang chuẩn bị dữ liệu cho tệp {i+1}/{len(result['result'])}...")
                
        # Prepare for reanalysis
        llm = LLMProcessor(reanalyze_llm_model)
        
        # Extract content and times from original transcription
        align_result = file_result.get("align_result", {})
        
        update_processing_status(task_id, 0.1 + (i / len(result["result"]) * 0.6) + 0.3, 
                f"Đang phân tích lại tệp {i+1}/{len(result['result'])}...")
                
        # Reanalyze with new prompt
        narrative_segments = llm.segment_narrative(align_result, new_prompt)
        
        # Convert narrative segments to standard segments format
        segments = llm._convert_narrative_to_standard_segments(narrative_segments)
        
        # Save results
        file_results.append({
            "filename": file_result["filename"],
            "align_result": align_result,
            "segments": segments,
            "filepath": file_result["filepath"]
        })
    
    update_processing_status(task_id, 0.9, "Đang chuẩn bị kết quả...")
    
    # Format for display
    display_result = []
    clip_result = []
    
    for file_result in file_results:
        # Only keep top 5 segments by relevance (already sorted)
        top_segments = file_result["segments"][:5]
        for seg in top_segments:
            # Generate thumbnail at the middle of the segment
            thumbnail_path = ""
            try:
                video_path = file_result["filepath"]
                thumbnail_time = (seg['start'] + seg['end']) / 2  # Middle of segment
                thumbnail_filename = f"{file_result['filename']}_{seg['start']:.1f}_{seg['end']:.1f}.jpg"
                thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
                
                # Only generate thumbnail if it doesn't exist
                if not os.path.exists(thumbnail_path):
                    print(f"Generating thumbnail: {thumbnail_path}")
                    generated_path = VideoProcessor.extract_thumbnail(video_path, thumbnail_time, thumbnail_path)
                    if generated_path and os.path.exists(generated_path):
                        thumbnail_path = generated_path
                        print(f"Thumbnail generated successfully: {thumbnail_path}")
                    else:
                        print(f"Failed to generate thumbnail: {thumbnail_path}")
                        thumbnail_path = ""
                else:
                    print(f"Thumbnail already exists: {thumbnail_path}")
            except Exception as e:
                print(f"Error generating thumbnail: {str(e)}")
                thumbnail_path = ""
            
            # Create row for analysis results table
            row = [file_result["filename"],
                   f"{seconds_to_hhmmss(seg['start'])}",
                   f"{seconds_to_hhmmss(seg['end'])}",
                   f"{seconds_to_hhmmss(seg['end'] - seg['start'])}",
                   seg["summary"],
                   ", ".join(seg["tags"]) if isinstance(
                       seg["tags"], list) else seg["tags"],
                   thumbnail_path]  # Add thumbnail path
            display_result.append(row)
            
            # Create better relevance score display with normalization
            relevance_score = seg.get('relevance_score')
            if relevance_score is not None:
                normalized_score = normalize_relevancy_score(relevance_score)
                relevance_display = f"{normalized_score:.1f}/10"
            else:
                relevance_display = "N/A"
                print(f"[WARNING] Missing relevance_score for segment: {seg.get('summary', 'Unknown')}")
            
            # Create row for clipping options table
            clip_row = [
                CHECKBOX_UNCHECKED,  # Checkbox column
                file_result["filename"],  # Filename column
                f"{seconds_to_hhmmss(seg['start'])}",  # Start time
                f"{seconds_to_hhmmss(seg['end'])}",  # End time
                f"{seconds_to_hhmmss(seg['end'] - seg['start'])}",  # Duration
                seg["summary"],  # Summary
                ", ".join(seg["tags"]) if isinstance(seg["tags"], list) else seg["tags"],  # Tags
                relevance_display  # Relevance score
            ]
            clip_result.append(clip_row)
            
    update_processing_status(task_id, 1.0, "Hoàn tất phân tích!")
            
    return {
        "task_id": task_id,
        "status": f"Kết quả phân tích cho chủ đề: {new_prompt}",
        "raw_result": file_results,
        "result": display_result,
        "progress": 1.0,
        "progress_desc": f"Phân tích hoàn tất cho chủ đề: {new_prompt}"
    }, clip_result


def create_gradio_interface():
    """Create Gradio Interface"""
    with gr.Blocks(theme=gr.themes.Soft()) as app:
        gr.Markdown("""# PreenCut - Ứng dụng phân tích video/âm thanh
            Tải lên các tệp video/âm thanh để xử lý và phân tích, hỗ trợ các định dạng mp4, mp3, wav, avi, mov, v.v.
            """)

        with gr.Row():
            with gr.Column(scale=1):
                with gr.Row():
                    with gr.Column(scale=3):
                        upload_files = gr.File(label="Tệp tải lên", file_count="multiple")
                    with gr.Column(scale=2):
                        with gr.Row():
                            start_btn = gr.Button("Bắt đầu xử lý", variant="primary", scale=3)
                with gr.Row():
                    # Status components - simplified since progress is now in footer
                    with gr.Column():
                        progress_desc = gr.HTML(label="Trạng thái", value="<p style='color: #6b7280; font-style: italic;'>Sẵn sàng xử lý tệp</p>")
                    status_display = gr.JSON(label="Thông tin chi tiết", visible=False)
                    task_id = gr.Textbox(visible=False)

            with gr.Column(scale=3):
                with gr.Tab("Tóm tắt nội dung"):
                    gr.Markdown("### 📝 Tóm tắt nội dung tự động")
                    transcription_summary = gr.Markdown(
                        value="## 📋 Đang chờ xử lý\n\nTóm tắt sẽ hiển thị ở đây sau khi xử lý. Tóm tắt này sẽ được tạo tự động bằng AI từ toàn bộ nội dung video.",
                        label="Tóm tắt nội dung livestream"
                    )
                gr.Interface
                with gr.Tab("Trích xuất phân đoạn theo chủ đề"):
                    gr.Markdown("""
                    ### Trích xuất phân đoạn theo chủ đề
                    Tính năng này sử dụng đầu ra có cấu trúc của Ollama để tìm **các phân đoạn hoàn chỉnh** nơi chủ đề được chỉ định được thảo luận.
                    Nó sẽ xác định tất cả các trường hợp với dấu thời gian chính xác và trích xuất toàn bộ ngữ cảnh.
                    """)
                    
                    new_prompt = gr.Textbox(
                        label="Nhập chủ đề hoặc nội dung cụ thể cần trích xuất",
                        placeholder="Ví dụ: Tìm các phân đoạn thảo luận về triệu chứng cúm ở trẻ nhỏ",
                        lines=2,
                        info="Hãy cụ thể về nội dung bạn đang tìm kiếm. Truy vấn càng chính xác, kết quả càng tốt."
                    )
                    reanalyze_btn = gr.Button("Trích xuất phân đoạn theo chủ đề", variant="secondary")

                with gr.Tab("Tùy chọn cắt"):
                    segment_selection = gr.Dataframe(
                        headers=["Chọn", "Tên tệp", "Thời gian bắt đầu", "Thời gian kết thúc", "Thời lượng",
                                 "Tóm tắt", "Từ khóa", "Điểm liên quan"],
                        datatype=['html', 'str', 'str', 'str', 'str', 'str', 'str', 'str'],
                        column_widths=[60, 120, 100, 100, 80, 300, 150, 100],
                        interactive=False,
                        wrap=True,
                        type="array",
                        label="Chọn các đoạn bạn muốn giữ lại - Sắp xếp theo điểm tổng hợp (cao nhất trước)"
                    )
                    
                    # Selection control buttons
                    with gr.Row():
                        select_all_btn = gr.Button("Chọn tất cả", variant="secondary", size="sm")
                        deselect_all_btn = gr.Button("Bỏ chọn tất cả", variant="secondary", size="sm")
                    
                    # Function to toggle selection
                    def select_clip_and_toggle(segment_selection: List[List], evt: gr.SelectData) -> List[List]:
                        selected_row = segment_selection[evt.index[0]]
                        # Toggle selection state for checkbox column (index 0)
                        selected_row[0] = CHECKBOX_CHECKED \
                            if selected_row[0] == CHECKBOX_UNCHECKED else CHECKBOX_UNCHECKED
                        
                        return segment_selection
                    
                    # Connect selection event
                    segment_selection.select(
                        select_clip_and_toggle,
                        inputs=segment_selection,
                        outputs=[segment_selection]
                    )
                    # Add download mode selection
                    download_mode = gr.Radio(
                        choices=["Đóng gói thành tệp zip", "Ghép thành một tệp"],
                        label="Cách xử lý khi nhiều tệp được chọn",
                        value="Đóng gói thành tệp zip"
                    )
                    clip_btn = gr.Button("Biên tập", variant="primary")
                    download_output = gr.File(label="Tải xuống kết quả cắt")

        # Progress bar footer - dedicated space at the bottom of the page
        with gr.Row():
            with gr.Column():
                gr.Markdown("---")  # Separator line
                footer_progress = gr.HTML(
                    label="🔄 Tiến trình xử lý", 
                    value="""
                    <div style="margin: 20px 0; padding: 20px; background: #f8fafc; border-radius: 10px; text-align: center; font-family: system-ui, -apple-system, sans-serif;">
                        <div style="font-size: 16px; font-weight: 500; color: #374151; margin-bottom: 10px;">
                            ⏳ Chưa có tác vụ nào đang xử lý
                        </div>
                        <div style="font-size: 14px; color: #6b7280;">
                            Tiến trình xử lý sẽ hiển thị ở đây khi bạn bắt đầu xử lý tệp
                        </div>
                    </div>
                    """,
                    visible=True
                )



        # Schedule the status update loop with selection preservation
        def check_status_with_selection(task_id, current_selection):
            status, result_table_data, clip_data = check_status(task_id, current_selection)
            # Stop timer if processing is complete or there's an error
            if status.get("status") in ["Xử lý hoàn tất", "Lỗi"] or status.get("status", "").startswith("Lỗi:"):
                return status, clip_data, gr.Timer(active=False)
            return status, clip_data, gr.Timer(active=True)
            
        timer = gr.Timer(1, active=False)  # Update every 1 second for smoother progress
        timer.tick(check_status_with_selection, [task_id, segment_selection],
                   outputs=[status_display, segment_selection, timer])

        # Update progress description when status changes (with debouncing to reduce flicker)
        last_progress_update = {"time": 0, "desc": ""}
        
        def update_footer_progress(status_info):
            current_time = time.time()
            desc = status_info.get("progress_desc", "")
            progress = status_info.get("progress", 0.0)
            
            print(f"[DEBUG] update_footer_progress called: progress={progress:.2f}, desc='{desc}'")
            
            # Only update if enough time has passed or status changed significantly
            if (current_time - last_progress_update["time"] > 0.2 or 
                desc != last_progress_update["desc"]):
                last_progress_update["time"] = current_time
                last_progress_update["desc"] = desc
                
                # Create footer-style progress bar with enhanced design
                if progress > 0 and progress < 1.0:
                    percentage = min(100, int(progress * 100))
                    html_content = f"""
                    <div style="
                        margin: 20px 0; 
                        padding: 25px; 
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                        border-radius: 15px; 
                        color: white;
                        font-family: system-ui, -apple-system, sans-serif;
                        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                        position: relative;
                        overflow: hidden;
                    ">
                        <!-- Background animation -->
                        <div style="
                            position: absolute;
                            top: 0;
                            left: 0;
                            right: 0;
                            bottom: 0;
                            background: linear-gradient(45deg, transparent 30%, rgba(255,255,255,0.1) 50%, transparent 70%);
                            animation: shimmer 2s infinite;
                        "></div>
                        
                        <div style="position: relative; z-index: 1;">
                            <div style="
                                display: flex; 
                                justify-content: space-between; 
                                align-items: center; 
                                margin-bottom: 15px;
                            ">
                                <div style="font-size: 18px; font-weight: 600;">
                                    🔄 Đang xử lý...
                                </div>
                                <div style="font-size: 16px; font-weight: 500;">
                                    {percentage}%
                                </div>
                            </div>
                            
                            <div style="margin-bottom: 15px; font-size: 14px; opacity: 0.9;">
                                {desc}
                            </div>
                            
                            <div style="
                                background: rgba(255,255,255,0.2); 
                                border-radius: 25px; 
                                overflow: hidden; 
                                height: 12px;
                                position: relative;
                            ">
                                <div style="
                                    background: linear-gradient(90deg, #ffffff 0%, #f0f9ff 100%);
                                    height: 100%;
                                    border-radius: 25px;
                                    width: {percentage}%;
                                    transition: width 0.5s ease;
                                    box-shadow: 0 2px 10px rgba(255,255,255,0.3);
                                "></div>
                            </div>
                        </div>
                        
                        <style>
                            @keyframes shimmer {{
                                0% {{ transform: translateX(-100%); }}
                                100% {{ transform: translateX(200%); }}
                            }}
                        </style>
                    </div>
                    """
                    print(f"[DEBUG] Generated footer progress bar HTML for {percentage}%")
                elif desc and progress >= 1.0:
                    # Completion state
                    html_content = f"""
                    <div style="
                        margin: 20px 0; 
                        padding: 25px; 
                        background: linear-gradient(135deg, #10b981 0%, #065f46 100%); 
                        border-radius: 15px; 
                        color: white;
                        font-family: system-ui, -apple-system, sans-serif;
                        box-shadow: 0 10px 30px rgba(16,185,129,0.3);
                        text-align: center;
                    ">
                        <div style="font-size: 20px; font-weight: 600; margin-bottom: 10px;">
                            ✅ Xử lý hoàn tất!
                        </div>
                        <div style="font-size: 14px; opacity: 0.9;">
                            {desc}
                        </div>
                    </div>
                    """
                    print(f"[DEBUG] Generated completion HTML: {desc}")
                elif desc and ("lỗi" in desc.lower() or "error" in desc.lower()):
                    # Error state
                    html_content = f"""
                    <div style="
                        margin: 20px 0; 
                        padding: 25px; 
                        background: linear-gradient(135deg, #ef4444 0%, #991b1b 100%); 
                        border-radius: 15px; 
                        color: white;
                        font-family: system-ui, -apple-system, sans-serif;
                        box-shadow: 0 10px 30px rgba(239,68,68,0.3);
                        text-align: center;
                    ">
                        <div style="font-size: 20px; font-weight: 600; margin-bottom: 10px;">
                            ❌ Có lỗi xảy ra
                        </div>
                        <div style="font-size: 14px; opacity: 0.9;">
                            {desc}
                        </div>
                    </div>
                    """
                    print(f"[DEBUG] Generated error HTML: {desc}")
                else:
                    # Idle state
                    html_content = """
                    <div style="margin: 20px 0; padding: 20px; background: #f8fafc; border-radius: 10px; text-align: center; font-family: system-ui, -apple-system, sans-serif;">
                        <div style="font-size: 16px; font-weight: 500; color: #374151; margin-bottom: 10px;">
                            ⏳ Chưa có tác vụ nào đang xử lý
                        </div>
                        <div style="font-size: 14px; color: #6b7280;">
                            Tiến trình xử lý sẽ hiển thị ở đây khi bạn bắt đầu xử lý tệp
                        </div>
                    </div>
                    """
                    print("[DEBUG] Generated idle state HTML")
                    
                return html_content
            return gr.update()
            
        # Also update the simple status in the status column
        def update_simple_status(status_info):
            """Update simple status text in the status column"""
            status = status_info.get("status", "")
            progress = status_info.get("progress", 0.0)
            
            if progress > 0 and progress < 1.0:
                return f"<p style='color: #3b82f6; font-weight: 500;'>⏳ Đang xử lý... ({int(progress*100)}%)</p>"
            elif "hoàn tất" in status.lower():
                return f"<p style='color: #10b981; font-weight: 500;'>✅ {status}</p>"
            elif "lỗi" in status.lower():
                return f"<p style='color: #ef4444; font-weight: 500;'>❌ {status}</p>"
            else:
                return f"<p style='color: #6b7280;'>{status or 'Sẵn sàng xử lý tệp'}</p>"
        
        # Update both footer progress and status column
        status_display.change(
            update_simple_status,
            inputs=status_display,
            outputs=progress_desc,
            show_progress=False
        )
        
        # Monitor status changes to update footer progress bar
        status_display.change(
            update_footer_progress,
            inputs=status_display,
            outputs=footer_progress,
            show_progress=False  # Hide the automatic progress indicator
        )

        # Automatically load summary when processing completes
        def handle_completion(status_info):
            if status_info and status_info.get("status") == "Xử lý hoàn tất":
                task_id = status_info.get("task_id")
                if task_id:
                    print(f"[DEBUG] Processing completed for task {task_id}, loading summary...")
                    try:
                        summary = get_transcription_summary_for_task(task_id)
                        print(f"[DEBUG] Summary loaded: {len(summary)} characters")
                        return summary
                    except Exception as e:
                        print(f"[ERROR] Failed to load summary: {e}")
                        return """
## ⚠️ Lỗi tải tóm tắt

Có lỗi xảy ra khi tải tóm tắt nội dung. Vui lòng thử lại.
                        """
            return gr.update()
        
        status_display.change(
            handle_completion,
            inputs=status_display,
            outputs=transcription_summary,
            show_progress=False
        )

        # Event bindings  
        def start_processing_and_monitoring(files):
            """Start processing and immediately activate monitoring"""
            task_id, initial_status = process_files_with_progress(files)
            
            # Create initial footer progress HTML
            initial_footer_html = """
            <div style="
                margin: 20px 0; 
                padding: 25px; 
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                border-radius: 15px; 
                color: white;
                font-family: system-ui, -apple-system, sans-serif;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
                position: relative;
                overflow: hidden;
            ">
                <div style="position: relative; z-index: 1;">
                    <div style="
                        display: flex; 
                        justify-content: space-between; 
                        align-items: center; 
                        margin-bottom: 15px;
                    ">
                        <div style="font-size: 18px; font-weight: 600;">
                            🚀 Bắt đầu xử lý...
                        </div>
                        <div style="font-size: 16px; font-weight: 500;">
                            5%
                        </div>
                    </div>
                    
                    <div style="margin-bottom: 15px; font-size: 14px; opacity: 0.9;">
                        Khởi tạo tác vụ...
                    </div>
                    
                    <div style="
                        background: rgba(255,255,255,0.2); 
                        border-radius: 25px; 
                        overflow: hidden; 
                        height: 12px;
                        position: relative;
                    ">
                        <div style="
                            background: linear-gradient(90deg, #ffffff 0%, #f0f9ff 100%);
                            height: 100%;
                            border-radius: 25px;
                            width: 5%;
                            transition: width 0.5s ease;
                            box-shadow: 0 2px 10px rgba(255,255,255,0.3);
                        "></div>
                    </div>
                </div>
            </div>
            """
            
            return task_id, initial_status, gr.Timer(active=True), initial_footer_html
        
        start_btn.click(
            start_processing_and_monitoring,
            inputs=[upload_files],
            outputs=[task_id, status_display, timer, footer_progress],
            show_progress=True  # Show the floating progress bar as well
        )
        
        # Remove get_summary_btn and related click event (no longer needed)
        # The summary will be generated and displayed automatically after processing

        reanalyze_btn.click(
            start_reanalyze,
            inputs=None,
            outputs=status_display,
        ).then(
            reanalyze_with_prompt,
            inputs=[task_id, new_prompt],
            outputs=[status_display, segment_selection]
        )

        clip_btn.click(
            clip_and_download,
            inputs=[status_display, segment_selection, download_mode],
            outputs=download_output
        )

        select_all_btn.click(
            select_all_clips,
            inputs=[segment_selection],
            outputs=[segment_selection]
        )

        deselect_all_btn.click(
            deselect_all_clips,
            inputs=[segment_selection],
            outputs=[segment_selection]
        )

        # Removed chapter-related functionality - replaced with simple transcription summary
        
        return app


def select_all_clips(segment_selection: List[List]) -> List[List]:
    """Select all clips in the selection table"""
    if not segment_selection:
        return segment_selection
    
    # Set all checkboxes to checked
    for row in segment_selection:
        if len(row) > 0:
            row[0] = CHECKBOX_CHECKED
    
    return segment_selection


def deselect_all_clips(segment_selection: List[List]) -> List[List]:
    """Deselect all clips in the selection table"""
    if not segment_selection:
        return segment_selection
    
    # Set all checkboxes to unchecked
    for row in segment_selection:
        if len(row) > 0:
            row[0] = CHECKBOX_UNCHECKED
    
    return segment_selection
