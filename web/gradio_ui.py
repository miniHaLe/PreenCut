import os
import uuid
import time
import random
import zipfile
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
from utils import seconds_to_hhmmss, hhmmss_to_seconds, clear_directory_fast \
    , generate_safe_filename
from typing import List, Dict, Tuple, Optional, Any, Union
import subprocess

# Global instance
processing_queue = ProcessingQueue()
CHECKBOX_CHECKED = '<span style="display: flex; width: 16px; height: 16px; border: 2px solid blue; background:#4B6BFB ;font-weight: bold;color:white;align-items:center;justify-content:center">✓</span>'
CHECKBOX_UNCHECKED = '<span style="display: flex; width: 16px; height: 16px; border: 2px solid blue;font-weight: bold;color:white;align-items:center;justify-content:center"></span>'


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
        ext = os.path.splitext(filename)[1][1:].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise gr.Error(
                f"Định dạng tệp không được hỗ trợ: {ext}, Chỉ hỗ trợ: {', '.join(ALLOWED_EXTENSIONS)}")

        saved_paths.append(file.name)

    return saved_paths


def process_files_with_progress(files: List, llm_model: str,
                  prompt: Optional[str] = None,
                  whisper_model_size: Optional[str] = None,
                  progress=gr.Progress()) -> Tuple[str, Dict, List, List]:
    """Processing uploaded files with real-time progress"""
    
    # Check whether the uploaded files meet the requirements
    saved_paths = check_uploaded_files(files)
    
    # Create a unique task ID
    task_id = f"task_{uuid.uuid4().hex}"
    
    progress(0.01, desc="Khởi tạo tác vụ...")
    time.sleep(0.1)  # Small delay to show progress
    
    print(f"Bắt đầu xử lý: {task_id}, Đường dẫn tệp: {saved_paths}", flush=True)

    # Process files directly with progress
    from modules.speech_recognizers.speech_recognizer_factory import SpeechRecognizerFactory
    from modules.llm_processor import LLMProcessor
    from modules.video_processor import VideoProcessor
    from config import SPEECH_RECOGNIZER_TYPE, ENABLE_ALIGNMENT
    
    progress(0.05, desc="Khởi tạo các mô hình...")
    
    try:
        # Initialize models
        recognizer = SpeechRecognizerFactory.get_speech_recognizer_by_type(
            SPEECH_RECOGNIZER_TYPE, whisper_model_size)
        llm = LLMProcessor(llm_model)
        
        progress(0.1, desc="Đã khởi tạo các mô hình")
        
        # Process each file with progress
        file_results = []
        total_files = len(saved_paths)
        
        for i, file_path in progress.tqdm(enumerate(saved_paths), desc="Xử lý từng tệp", total=total_files):
            file_progress_base = 0.1 + (i / total_files) * 0.8
            file_progress_weight = 0.8 / total_files
            
            progress(file_progress_base, desc=f"Đang xử lý tệp {i + 1}/{total_files}: {os.path.basename(file_path)}")
            
            # Extract audio (if video)
            if file_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.ts', '.mxf')):
                progress(file_progress_base + file_progress_weight * 0.1, 
                        desc=f"Trích xuất âm thanh từ {os.path.basename(file_path)}")
                audio_path = VideoProcessor.extract_audio(file_path, task_id)
            else:
                audio_path = file_path

            # Speech Recognition
            progress(file_progress_base + file_progress_weight * 0.2, 
                    desc=f"Nhận dạng giọng nói: {os.path.basename(file_path)}")
            
            print(f"Bắt đầu nhận dạng giọng nói: {file_path}")
            result = recognizer.transcribe(audio_path)
            print(f"Hoàn thành nhận dạng giọng nói, số phân đoạn: {len(result['segments'])}")

            # Text Alignment (if enabled)
            if ENABLE_ALIGNMENT:
                progress(file_progress_base + file_progress_weight * 0.6, 
                        desc=f"Căn chỉnh văn bản: {os.path.basename(file_path)}")
                from modules.text_aligner import TextAligner
                aligner = TextAligner(result['language'])
                result = aligner.align(result["segments"], audio_path)

            # LLM Processing
            progress(file_progress_base + file_progress_weight * 0.8, 
                    desc=f"Phân tích và tóm tắt: {os.path.basename(file_path)}")
            
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
            
            progress(file_progress_base + file_progress_weight, 
                    desc=f"Hoàn thành tệp {i + 1}/{total_files}")
        
        progress(0.95, desc="Chuẩn bị kết quả hiển thị...")
        
        # Prepare results for display
        display_result = []
        clip_result = []
        
        # Create a directory for thumbnails
        thumbnail_dir = os.path.join(TEMP_FOLDER, "thumbnails", task_id)
        os.makedirs(thumbnail_dir, exist_ok=True)
        
        for file_result in file_results:
            for seg in file_result["segments"]:
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
                
                # Create row for analysis results table
                row = [file_result["filename"],
                       f"{seconds_to_hhmmss(seg['start'])}",
                       f"{seconds_to_hhmmss(seg['end'])}",
                       f"{seconds_to_hhmmss(seg['end'] - seg['start'])}",
                       seg["summary"],
                       ", ".join(seg["tags"]) if isinstance(seg["tags"], list) else seg["tags"],
                       thumbnail_path]
                display_result.append(row)
                
                # Create row for clipping options table
                clip_row = [
                    CHECKBOX_UNCHECKED,
                    file_result["filename"],
                    f"{seconds_to_hhmmss(seg['start'])}",
                    f"{seconds_to_hhmmss(seg['end'])}",
                    f"{seconds_to_hhmmss(seg['end'] - seg['start'])}",
                    seg["summary"],
                    ", ".join(seg["tags"]) if isinstance(seg["tags"], list) else seg["tags"],
                    thumbnail_path
                ]
                clip_result.append(clip_row)
        
        # Store results in the processing queue for later access
        with processing_queue.lock:
            processing_queue.results[task_id] = {
                "status": "completed",
                "result": file_results,
                "timestamp": time.time(),
                "progress": 1.0,
                "progress_desc": "Xử lý hoàn tất"
            }
        
        progress(1.0, desc="Hoàn tất xử lý!")
        
        return (task_id, 
                {"task_id": task_id, "status": "Xử lý hoàn tất",
                 "raw_result": file_results, "result": display_result,
                 "progress": 1.0, "progress_desc": "Xử lý hoàn tất"},
                display_result, 
                clip_result)
        
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
        
        raise gr.Error(f"Lỗi xử lý: {str(e)}")


def process_files(files: List, llm_model: str,
                  prompt: Optional[str] = None,
                  whisper_model_size: Optional[str] = None,
                  progress=gr.Progress()) -> Tuple[str, Dict]:
    """Processing uploaded files (legacy function for compatibility)"""

    # Check whether the uploaded files meet the requirements
    saved_paths = check_uploaded_files(files)
    
    # Create a unique task ID
    task_id = f"task_{uuid.uuid4().hex}"
    
    progress(0.05, desc="Khởi tạo tác vụ...")

    print(f"Thêm tác vụ: {task_id}, Đường dẫn tệp: {saved_paths}", flush=True)

    # Add to the processing queue
    processing_queue.add_task(task_id, saved_paths, llm_model, prompt,
                              whisper_model_size)
    
    progress(0.1, desc="Đã thêm vào hàng đợi, đang xử lý...")

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
                viral_potential = seg.get('viral_potential', 'medium')
                composite_score = seg.get('composite_score', relevance_score * 0.6 + engagement_score * 0.4)
                
                # Format scores for display
                if isinstance(relevance_score, (int, float)):
                    relevance_display = f"{relevance_score:.1f}/10"
                else:
                    relevance_display = "5.0/10"
                
                if isinstance(viral_potential, str):
                    viral_display = {
                        'low': '🔵 Thấp',
                        'medium': '🟡 Trung bình', 
                        'high': '🔴 Cao'
                    }.get(viral_potential.lower(), '🟡 Trung bình')
                else:
                    viral_display = '🟡 Trung bình'
                
                clip_row = [
                    checkbox_state,  # Checkbox column - preserve state
                    file_result["filename"],  # Filename column
                    f"{seconds_to_hhmmss(seg['start'])}",  # Start time
                    f"{seconds_to_hhmmss(seg['end'])}",  # End time
                    f"{seconds_to_hhmmss(seg['end'] - seg['start'])}",  # Duration
                    seg["summary"],  # Summary
                    ", ".join(seg["tags"]) if isinstance(seg["tags"], list) else seg["tags"],  # Tags
                    str(word_count),  # Word count
                    relevance_display,  # Relevance score
                    viral_display,  # Viral potential
                    thumbnail_path  # Thumbnail path
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


def reanalyze_with_prompt(task_id: str, reanalyze_llm_model: str,
                          new_prompt: str,
                          progress=gr.Progress()) -> Tuple[Dict, List[List], List[List]]:
    """Reanalysis with specific prompt"""
    if not task_id:
        raise gr.Error("Không có tác vụ xử lý nào đang hoạt động")

    if not new_prompt:
        raise gr.Error("Vui lòng nhập chủ đề cần trích xuất")

    # Get current results
    result = processing_queue.get_result(task_id)
    if result["status"] != "completed":
        raise gr.Error("Tác vụ chưa hoàn thành, vui lòng đợi")

    progress(0.1, desc="Đang khởi tạo phân tích mới...")
    
    # Create a directory for thumbnails if it doesn't exist
    thumbnail_dir = os.path.join(TEMP_FOLDER, "thumbnails", task_id)
    os.makedirs(thumbnail_dir, exist_ok=True)
    
    # Get raw data for reanalysis
    file_results = []
    
    for i, file_result in progress.tqdm(enumerate(result["result"]), desc="Phân tích từng tệp", total=len(result["result"])):
        progress(0.1 + (i / len(result["result"]) * 0.6), 
                desc=f"Đang chuẩn bị dữ liệu cho tệp {i+1}/{len(result['result'])}...")
                
        # Prepare for reanalysis
        llm = LLMProcessor(reanalyze_llm_model)
        
        # Extract content and times from original transcription
        align_result = file_result.get("align_result", {})
        
        progress(0.1 + (i / len(result["result"]) * 0.6) + 0.3, 
                desc=f"Đang phân tích lại tệp {i+1}/{len(result['result'])}...")
                
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
    
    progress(0.9, desc="Đang chuẩn bị kết quả...")
    
    # Format for display
    display_result = []
    clip_result = []
    
    for file_result in file_results:
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
            
            # Create row for clipping options table
            clip_row = [
                CHECKBOX_UNCHECKED,  # Checkbox column
                file_result["filename"],  # Filename column
                f"{seconds_to_hhmmss(seg['start'])}",  # Start time
                f"{seconds_to_hhmmss(seg['end'])}",  # End time
                f"{seconds_to_hhmmss(seg['end'] - seg['start'])}",  # Duration
                seg["summary"],  # Summary
                ", ".join(seg["tags"]) if isinstance(seg["tags"], list) else seg["tags"],  # Tags
                thumbnail_path  # Add thumbnail path
            ]
            clip_result.append(clip_row)
            
    progress(1.0, desc="Hoàn tất phân tích!")
            
    return {
        "task_id": task_id,
        "status": f"Kết quả phân tích cho chủ đề: {new_prompt}",
        "raw_result": file_results,
        "result": display_result,
        "progress": 1.0,
        "progress_desc": f"Phân tích hoàn tất cho chủ đề: {new_prompt}"
    }, display_result, clip_result


def optimize_for_social_media(task_id: str, platform: str, prompt: str, llm_model: str, 
                            content_style: str, max_clips: int, progress=gr.Progress()) -> List[List]:
    """Optimize video content for social media platforms"""
    
    if not task_id:
        raise gr.Error("Không tìm thấy task ID")
    
    task_result = processing_queue.get_result(task_id)
    if not task_result or "result" not in task_result:
        raise gr.Error("Không có nội dung để tối ưu hóa")
    
    if not prompt:
        raise gr.Error("Vui lòng nhập chủ đề nội dung")
    
    if not llm_model:
        raise gr.Error("Vui lòng chọn mô hình AI")
    
    progress(0.1, desc="Khởi tạo tối ưu hóa social media...")
    
    try:
        from modules.llm_processor import LLMProcessor
        llm = LLMProcessor(llm_model)
        
        all_social_segments = []
        total_files = len(task_result["result"])
        
        progress(0.2, desc=f"Phân tích {total_files} file cho {platform}...")
        
        for i, file_data in enumerate(task_result["result"]):
            file_progress = 0.2 + (i / total_files) * 0.6
            progress(file_progress, desc=f"Tối ưu hóa file {i+1}/{total_files} cho {platform}...")
            
            # Extract segments from align_result
            align_result = file_data["align_result"]
            
            # Create social media optimized prompt
            social_prompt = f"{prompt} - Phong cách: {content_style}"
            
            # Use social media optimization
            social_segments = llm.segment_video_for_social_media(
                align_result["segments"], 
                platform=platform, 
                prompt=social_prompt
            )
            
            # Get best clips for the platform
            best_clips = llm.get_best_clips_for_platform(social_segments, platform, max_clips)
            
            # Add file context to segments
            for segment in best_clips:
                segment['filename'] = file_data['filename']
                segment['filepath'] = file_data['filepath']
                
            all_social_segments.extend(best_clips)
        
        progress(0.8, desc="Tạo thumbnail và xếp hạng...")
        
        # Sort all segments by composite score
        all_social_segments.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
        
        # Take only the best clips overall
        final_clips = all_social_segments[:max_clips]
        
        # Generate thumbnails and create display data
        social_result_data = []
        
        for i, segment in enumerate(final_clips):
            file_progress = 0.8 + (i / len(final_clips)) * 0.15
            progress(file_progress, desc=f"Tạo thumbnail {i+1}/{len(final_clips)}...")
            
            # Generate thumbnail
            thumbnail_path = ""
            try:
                video_path = segment['filepath']
                if video_path and os.path.exists(video_path):
                    thumbnail_dir = os.path.join(TEMP_FOLDER, "thumbnails")
                    os.makedirs(thumbnail_dir, exist_ok=True)
                    
                    thumbnail_time = (segment['start'] + segment['end']) / 2
                    thumbnail_filename = f"{platform}_{segment['filename']}_{segment['start']:.1f}_{segment['end']:.1f}.jpg"
                    thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
                    
                    if not os.path.exists(thumbnail_path):
                        from modules.video_processor import VideoProcessor
                        generated_path = VideoProcessor.extract_thumbnail(video_path, thumbnail_time, thumbnail_path)
                        if generated_path and os.path.exists(generated_path):
                            thumbnail_path = generated_path
                        else:
                            thumbnail_path = ""
                    
            except Exception as e:
                print(f"Error generating social media thumbnail: {str(e)}")
                thumbnail_path = ""
            
            # Format platform display
            platform_display = {
                'tiktok': '🎵 TikTok',
                'instagram': '📸 Instagram',
                'youtube_shorts': '🎬 YouTube',
                'general': '📱 Universal'
            }.get(platform, '📱 Universal')
            
            # Format duration
            duration = segment['end'] - segment['start']
            duration_display = f"{duration:.0f}s"
            
            # Format time range
            time_display = f"{seconds_to_hhmmss(segment['start'])} - {seconds_to_hhmmss(segment['end'])}"
            
            # Format engagement score
            engagement_score = segment.get('engagement_score', 5)
            engagement_display = f"{engagement_score:.1f}/10 ⭐"
            
            # Format viral potential
            viral_potential = segment.get('viral_potential', 'medium')
            viral_display = {
                'low': '🔵 Thấp',
                'medium': '🟡 Trung bình',
                'high': '🔴 Cao'
            }.get(viral_potential.lower(), '🟡 Trung bình')
            
            # Format hashtags
            tags = segment.get('tags', [])
            hashtags = ' '.join([f"#{tag}" for tag in tags[:5]])  # Limit to 5 hashtags
            
            row = [
                CHECKBOX_UNCHECKED,  # Selection checkbox
                platform_display,  # Platform
                time_display,  # Time range
                duration_display,  # Duration
                segment.get('summary', 'Clip viral'),  # Title
                segment.get('hook_text', 'Bạn có biết...'),  # Hook
                hashtags,  # Hashtags
                engagement_display,  # Engagement score
                viral_display,  # Viral potential
                thumbnail_path  # Thumbnail
            ]
            
            social_result_data.append(row)
        
        progress(1.0, desc=f"Hoàn tất! Tạo được {len(final_clips)} clip viral cho {platform}")
        
        return social_result_data
        
    except Exception as e:
        error_msg = f"Lỗi tối ưu hóa social media: {str(e)}"
        print(error_msg)
        raise gr.Error(error_msg)


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
                    whisper_model_size = gr.Dropdown(
                        choices=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
                        value=WHISPER_MODEL_SIZE,
                        label="Kích thước mô hình Whisper",
                        interactive=True
                    )
                    llm_model = gr.Dropdown(
                        choices=[model['label'] for model in LLM_MODEL_OPTIONS],
                        value=LLM_MODEL_OPTIONS[0]['label'] if LLM_MODEL_OPTIONS else None,
                        label="Mô hình ngôn ngữ lớn",
                        interactive=True
                    )
                with gr.Row():
                    prompt = gr.Textbox(
                        lines=3,
                        placeholder="""Tùy chọn: Nhập mô tả chi tiết về cách bạn muốn nội dung của bạn được phân tích. 
                        Ví dụ: "Tôi muốn phân tích video này theo chủ đề kinh tế" hoặc "Tôi muốn tìm các phần nói về thị trường chứng khoán".""",
                        label="Gợi ý phân tích (tùy chọn)",
                        interactive=True
                    )
                with gr.Row():
                    # Status components
                    with gr.Column():
                        progress_desc = gr.Textbox(label="Trạng thái", interactive=False)
                    status_display = gr.JSON(label="Thông tin chi tiết", visible=False)
                    task_id = gr.Textbox(visible=False)

            with gr.Column(scale=3):
                with gr.Tab("Phân tích kết quả"):
                    result_table = gr.Dataframe(
                        headers=["Tên tệp", "Thời gian bắt đầu", "Thời gian kết thúc", "Thời lượng",
                                 "Tóm tắt", "Nhãn", "Hình thu nhỏ"],
                        datatype=["str", "str", "str", "str", "str", "str", "str"],
                        interactive=False,
                        wrap=True
                    )
                    
                    # Display thumbnails for selected segment
                    with gr.Row():
                        selected_thumbnail = gr.Image(label="Hình thu nhỏ của phân đoạn đã chọn", 
                                                     show_label=True, 
                                                     height=200)
                    
                    # Function to update thumbnail when a row is selected
                    def update_thumbnail(evt: gr.SelectData, results):
                        if evt.index[0] < len(results) and len(results[evt.index[0]]) > 6:
                            thumbnail_path = results[evt.index[0]][6]  # Get thumbnail path from the 7th column
                            if thumbnail_path and os.path.exists(thumbnail_path):
                                return thumbnail_path
                        return None
                    
                    # Connect selection event to update thumbnail
                    result_table.select(
                        update_thumbnail,
                        inputs=result_table,
                        outputs=selected_thumbnail
                    )

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
                    reanalyze_llm_model = gr.Dropdown(
                        choices=[model['label'] for model in LLM_MODEL_OPTIONS],
                        value= "llama3.1", 
                        label="Mô hình ngôn ngữ lớn"
                    )
                    reanalyze_btn = gr.Button("Trích xuất phân đoạn theo chủ đề", variant="secondary")

                with gr.Tab("Tùy chọn cắt"):
                    segment_selection = gr.Dataframe(
                        headers=["Chọn", "Tên tệp", "Thời gian bắt đầu", "Thời gian kết thúc", "Thời lượng",
                                 "Tóm tắt", "Từ khóa", "Số từ", "Điểm liên quan", "Tiềm năng viral", "Hình thu nhỏ"],
                        datatype='html',
                        interactive=False,
                        wrap=True,
                        type="array",
                        label="Chọn các đoạn bạn muốn giữ lại - Sắp xếp theo điểm tổng hợp (cao nhất trước)"
                    )
                    
                    # Selection control buttons
                    with gr.Row():
                        select_all_btn = gr.Button("Chọn tất cả", variant="secondary", size="sm")
                        deselect_all_btn = gr.Button("Bỏ chọn tất cả", variant="secondary", size="sm")
                    
                    # Display thumbnail for selected clip
                    with gr.Row():
                        clip_thumbnail = gr.Image(label="Hình thu nhỏ của phân đoạn đã chọn", 
                                                 show_label=True, 
                                                 height=200)
                    
                    # Function to toggle selection and update thumbnail
                    def select_clip_and_show_thumbnail(segment_selection: List[List], evt: gr.SelectData) -> Tuple[List[List], str]:
                        selected_row = segment_selection[evt.index[0]]
                        # Toggle selection state for checkbox column (index 0)
                        selected_row[0] = CHECKBOX_CHECKED \
                            if selected_row[0] == CHECKBOX_UNCHECKED else CHECKBOX_UNCHECKED
                        
                        # Get thumbnail path
                        thumbnail_path = ""
                        if len(selected_row) > 7:
                            thumbnail_path = selected_row[7]
                            
                        return segment_selection, thumbnail_path if thumbnail_path and os.path.exists(thumbnail_path) else None
                    
                    # Connect selection event
                    segment_selection.select(
                        select_clip_and_show_thumbnail,
                        inputs=segment_selection,
                        outputs=[segment_selection, clip_thumbnail]
                    )
                    # Add download mode selection
                    download_mode = gr.Radio(
                        choices=["Đóng gói thành tệp zip", "Ghép thành một tệp"],
                        label="Cách xử lý khi nhiều tệp được chọn",
                        value="Đóng gói thành tệp zip"
                    )
                    clip_btn = gr.Button("Biên tập", variant="primary")
                    download_output = gr.File(label="Tải xuống kết quả cắt")

                with gr.Tab("Tối ưu hóa cho mạng xã hội"):
                    gr.Markdown("""
                    ### 🚀 Tối ưu hóa nội dung cho TikTok, Instagram Reels, YouTube Shorts
                    Tính năng này phân tích video và tạo ra các clip ngắn được tối ưu hóa cho từng nền tảng mạng xã hội, 
                    tập trung vào viral potential và engagement.
                    """)
                    
                    with gr.Row():
                        with gr.Column():
                            social_platform = gr.Dropdown(
                                choices=[
                                    ("TikTok (15-180s, viral hooks)", "tiktok"),
                                    ("Instagram Reels (15-90s, aesthetic)", "instagram"), 
                                    ("YouTube Shorts (15-60s, retention)", "youtube_shorts"),
                                    ("Tổng hợp (tối ưu chung)", "general")
                                ],
                                value="tiktok",
                                label="Chọn nền tảng mục tiêu",
                                info="Mỗi nền tảng có chiến lược tối ưu khác nhau"
                            )
                            
                            social_prompt = gr.Textbox(
                                label="Chủ đề hoặc xu hướng muốn tạo nội dung",
                                placeholder="Ví dụ: Mẹo học tiếng Anh hiệu quả, Công thức nấu ăn viral, Tips làm đẹp...",
                                lines=2,
                                info="Mô tả nội dung bạn muốn tạo cho social media"
                            )
                            
                            max_clips = gr.Slider(
                                minimum=3,
                                maximum=10,
                                value=5,
                                step=1,
                                label="Số lượng clip tối đa",
                                info="Số clip viral nhất sẽ được chọn"
                            )
                            
                        with gr.Column():
                            social_llm_model = gr.Dropdown(
                                choices=[model['label'] for model in LLM_MODEL_OPTIONS],
                                value="llama3.1",
                                label="Mô hình AI để phân tích"
                            )
                            
                            content_style = gr.Radio(
                                choices=[
                                    ("Giáo dục/Thông tin", "educational"),
                                    ("Giải trí/Hài hước", "entertainment"),
                                    ("Cảm hứng/Động lực", "inspirational"),
                                    ("Tutorial/Hướng dẫn", "tutorial"),
                                    ("Trending/Xu hướng", "trending")
                                ],
                                value="educational",
                                label="Phong cách nội dung",
                                info="Xác định cách tiếp cận content"
                            )
                    
                    social_optimize_btn = gr.Button("🎯 Tạo nội dung viral", variant="primary", size="lg")
                    
                    # Results display for social media optimization
                    social_results = gr.Dataframe(
                        headers=["Chọn", "Nền tảng", "Thời gian", "Thời lượng", "Tiêu đề viral", "Hook", 
                                "Hashtags", "Điểm engagement", "Viral potential", "Thumbnail"],
                        datatype='html',
                        interactive=False,
                        wrap=True,
                        type="array",
                        label="Nội dung viral được tối ưu - Sắp xếp theo điểm engagement",
                        visible=False
                    )
                    
                    # Display thumbnail for selected social media clip
                    with gr.Row(visible=False) as social_thumbnail_row:
                        social_clip_thumbnail = gr.Image(label="Hình thu nhỏ của clip viral đã chọn", 
                                                        show_label=True, 
                                                        height=200)
                    
                    # Function to toggle selection and update thumbnail for social media
                    def select_social_clip_and_show_thumbnail(social_results: List[List], evt: gr.SelectData) -> Tuple[List[List], str]:
                        selected_row = social_results[evt.index[0]]
                        # Toggle selection state for checkbox column (index 0)
                        selected_row[0] = CHECKBOX_CHECKED \
                            if selected_row[0] == CHECKBOX_UNCHECKED else CHECKBOX_UNCHECKED
                        
                        # Get thumbnail path (column 9)
                        thumbnail_path = ""
                        if len(selected_row) > 9:
                            thumbnail_path = selected_row[9]
                            
                        return social_results, thumbnail_path if thumbnail_path and os.path.exists(thumbnail_path) else None
                    
                    # Connect selection event for social media results
                    social_results.select(
                        select_social_clip_and_show_thumbnail,
                        inputs=social_results,
                        outputs=[social_results, social_clip_thumbnail]
                    )
                    
                    # Selection controls for social media results
                    with gr.Row(visible=False) as social_controls:
                        social_select_all_btn = gr.Button("Chọn tất cả", variant="secondary", size="sm")
                        social_deselect_all_btn = gr.Button("Bỏ chọn tất cả", variant="secondary", size="sm")
                        social_download_btn = gr.Button("📱 Tải xuống clip viral", variant="primary", size="lg")
                    
                    # Download options for social media clips
                    with gr.Row(visible=False) as social_download_options:
                        social_download_mode = gr.Radio(
                            choices=["Đóng gói thành tệp zip", "Tải riêng lẻ theo nền tảng"],
                            label="Cách tải xuống",
                            value="Đóng gói thành tệp zip",
                            info="Zip: Tất cả clip trong 1 file | Riêng lẻ: Mỗi nền tảng 1 folder"
                        )
                    
                    social_download_output = gr.File(label="Tải xuống clip viral", visible=False)

        # Schedule the status update loop with selection preservation
        def check_status_with_selection(task_id, current_selection):
            status, result_table_data, clip_data = check_status(task_id, current_selection)
            # Stop timer if processing is complete or there's an error
            if status.get("status") in ["Xử lý hoàn tất", "Lỗi"] or status.get("status", "").startswith("Lỗi:"):
                return status, result_table_data, clip_data, gr.Timer(active=False)
            return status, result_table_data, clip_data, gr.Timer(active=True)
            
        timer = gr.Timer(2, active=False)
        timer.tick(check_status_with_selection, [task_id, segment_selection],
                   outputs=[status_display, result_table, segment_selection, timer])

        # Update progress description when status changes
        def update_progress_info(status_info):
            desc = status_info.get("progress_desc", "")
            return desc
            
        # Monitor status changes to update progress description
        status_display.change(
            update_progress_info,
            inputs=status_display,
            outputs=progress_desc
        )

        # Event bindings
        start_btn.click(
            process_files_with_progress,
            inputs=[upload_files, llm_model, prompt, whisper_model_size],
            outputs=[task_id, status_display, result_table, segment_selection]
        ).then(
            lambda: gr.Timer(active=False),  # No need for timer since we process directly
            outputs=timer,
            show_progress=False
        )

        reanalyze_btn.click(
            start_reanalyze,
            inputs=None,
            outputs=status_display,
        ).then(
            reanalyze_with_prompt,
            inputs=[task_id, reanalyze_llm_model, new_prompt],
            outputs=[status_display, result_table, segment_selection]
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

        social_optimize_btn.click(
            optimize_for_social_media,
            inputs=[task_id, social_platform, social_prompt, social_llm_model, content_style, max_clips],
            outputs=social_results
        ).then(
            lambda: (gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), 
                    gr.update(visible=True), gr.update(visible=True)),
            outputs=[social_results, social_controls, social_download_options, social_download_output, social_thumbnail_row]
        )

        # Event bindings for social media tab
        social_select_all_btn.click(
            select_all_clips,
            inputs=[social_results],
            outputs=[social_results]
        )

        social_deselect_all_btn.click(
            deselect_all_clips,
            inputs=[social_results],
            outputs=[social_results]
        )

        social_download_btn.click(
            download_social_media_clips,
            inputs=[task_id, social_results, social_download_mode],
            outputs=social_download_output
        )

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


def download_social_media_clips(task_id: str, social_results: List[List], download_mode: str) -> str:
    """Download selected social media optimized clips"""
    if not task_id:
        raise gr.Error("Không có tác vụ xử lý nào đang hoạt động")
    
    if not social_results:
        raise gr.Error("Chưa có kết quả tối ưu hóa nào")
    
    # Filter selected clips
    selected_clips = [clip for clip in social_results if clip[0] == CHECKBOX_CHECKED]
    
    if not selected_clips:
        raise gr.Error("Vui lòng chọn ít nhất một clip để tải xuống")
    
    # Get the original result to access file paths
    result = processing_queue.get_result(task_id)
    if not result or "data" not in result:
        raise gr.Error("Không tìm thấy dữ liệu tác vụ")
        
    # For testing purposes, also check if it's a completed result
    if result.get("status") == "completed" and "data" in result:
        file_data_source = result["data"]["raw_result"]
    elif "result" in result:  # Legacy format
        # Convert legacy format to expected format
        file_data_source = result["result"] 
    else:
        raise gr.Error("Định dạng dữ liệu không hợp lệ")
    
    # Create output directory
    task_output_dir = os.path.join(OUTPUT_FOLDER, f"social_media_{task_id}")
    if os.path.exists(task_output_dir):
        clear_directory_fast(task_output_dir)
    os.makedirs(task_output_dir, exist_ok=True)
    
    # Organize files into segments  
    file_segments = {}
    for file_data in file_data_source:
        file_segments[file_data["filename"]] = {
            "segments": file_data["segments"],
            "filepath": file_data["filepath"],
            "ext": os.path.splitext(file_data["filepath"])[1]
        }
    
    output_files = []
    platform_folders = {}
    
    for clip_data in selected_clips:
        # Extract info from social media clip data
        # Format: ["Chọn", "Nền tảng", "Thời gian", "Thời lượng", "Tiêu đề viral", "Hook", 
        #          "Hashtags", "Điểm engagement", "Viral potential", "Thumbnail"]
        platform = clip_data[1]
        time_range = clip_data[2]  # Format: "00:01:23 - 00:02:45"
        title = clip_data[4]
        
        # Parse time range
        try:
            start_str, end_str = time_range.split(' - ')
            start_seconds = hhmmss_to_seconds(start_str)
            end_seconds = hhmmss_to_seconds(end_str)
        except Exception as e:
            print(f"Error parsing time range {time_range}: {e}")
            continue
            
        # Find the corresponding file and segment
        clip_created = False
        for filename, file_info in file_segments.items():
            for segment in file_info["segments"]:
                # Check if this segment matches (with some tolerance)
                if (abs(segment["start"] - start_seconds) < 1.0 and 
                    abs(segment["end"] - end_seconds) < 1.0):
                    
                    # Create platform-specific folder if needed
                    if download_mode == "Tải riêng lẻ theo nền tảng":
                        if platform not in platform_folders:
                            platform_folder = os.path.join(task_output_dir, f"{platform}_clips")
                            os.makedirs(platform_folder, exist_ok=True)
                            platform_folders[platform] = platform_folder
                        output_folder = platform_folders[platform]
                    else:
                        output_folder = task_output_dir
                    
                    # Generate safe filename with viral title
                    safe_title = generate_safe_filename(title[:50])  # Limit length
                    safe_filename = f"{platform}_{safe_title}"
                    
                    # Clip the video
                    input_path = file_info["filepath"]
                    ext = file_info["ext"]
                    
                    output_path = os.path.join(output_folder, f"{safe_filename}{ext}")
                    
                    # Use ffmpeg to extract the clip
                    cmd = [
                        'ffmpeg', '-i', input_path,
                        '-ss', str(start_seconds),
                        '-t', str(end_seconds - start_seconds),
                        '-c', 'copy',
                        '-avoid_negative_ts', 'make_zero',
                        output_path
                    ]
                    
                    try:
                        subprocess.run(cmd, check=True, capture_output=True)
                        output_files.append(output_path)
                        clip_created = True
                        
                        # Create a metadata file with viral content info
                        metadata_path = os.path.join(output_folder, f"{safe_filename}_metadata.txt")
                        with open(metadata_path, 'w', encoding='utf-8') as f:
                            f.write(f"Nền tảng: {platform}\n")
                            f.write(f"Tiêu đề viral: {title}\n")
                            f.write(f"Hook: {clip_data[5]}\n")
                            f.write(f"Hashtags: {clip_data[6]}\n")
                            f.write(f"Điểm engagement: {clip_data[7]}\n")
                            f.write(f"Viral potential: {clip_data[8]}\n")
                            f.write(f"Thời gian: {time_range}\n")
                        
                        break
                        
                    except subprocess.CalledProcessError as e:
                        print(f"FFmpeg error: {e.stderr.decode('utf-8')}")
                        continue
                        
            if clip_created:
                break
    
    if not output_files:
        raise gr.Error("Không thể tạo clip nào. Vui lòng kiểm tra lại dữ liệu.")
    
    # Return result based on download mode
    if download_mode == "Đóng gói thành tệp zip":
        # Create zip file with all clips and metadata
        zip_path = os.path.join(task_output_dir, "viral_clips.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Add all video files and metadata
            for root, dirs, files in os.walk(task_output_dir):
                for file in files:
                    if file != "viral_clips.zip":  # Don't include the zip itself
                        file_path = os.path.join(root, file)
                        # Use relative path in zip
                        arcname = os.path.relpath(file_path, task_output_dir)
                        zipf.write(file_path, arcname)
        
        return zip_path
    else:
        # For platform-specific download, return the main directory
        return task_output_dir
