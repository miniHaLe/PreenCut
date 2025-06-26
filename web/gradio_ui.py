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
    MAX_FILE_NUMBERS
)
from modules.processing_queue import ProcessingQueue
from modules.video_processor import VideoProcessor
from utils import seconds_to_hhmmss, hhmmss_to_seconds, clear_directory_fast \
    , generate_safe_filename
from typing import List, Dict, Tuple, Optional
import subprocess

# 全局实例
processing_queue = ProcessingQueue()
CHECKBOX_CHECKED = '<span style="display: flex; width: 16px; height: 16px; border: 2px solid blue; background:#4B6BFB ;font-weight: bold;color:white;align-items:center;justify-content:center">✓</span>'
CHECKBOX_UNCHECKED = '<span style="display: flex; width: 16px; height: 16px; border: 2px solid blue;font-weight: bold;color:white;align-items:center;justify-content:center"></span>'


def check_uploaded_files(files: List) -> str:
    """Check if the uploaded file meets the requirements"""
    if not files:
        raise gr.Error("Please upload at least one file")

    if len(files) > MAX_FILE_NUMBERS:
        raise gr.Error(
            f"The number of uploaded files exceeds the limit ({len(files)} > {MAX_FILE_NUMBERS})")

    saved_paths = []
    for file in files:
        filename = os.path.basename(file.name)

        # Check the file size
        file_size = os.path.getsize(file.name)
        if file_size > MAX_FILE_SIZE:
            raise gr.Error(f"File size exceeds limit ({file_size} > {MAX_FILE_SIZE})")

        # Check the file format
        ext = os.path.splitext(filename)[1][1:].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise gr.Error(
                f"Unsupported file format: {ext}, Only supports: {', '.join(ALLOWED_EXTENSIONS)}")

        saved_paths.append(file.name)

    return saved_paths


def process_files(files: List, llm_model: str,
                  prompt: Optional[str] = None,
                  whisper_model_size: Optional[str] = None) -> Tuple[
    str, Dict]:
    """Processing uploaded files"""

    # 检查上传的文件是否符合要求
    saved_paths = check_uploaded_files(files)

    # 创建唯一任务ID
    task_id = f"task_{uuid.uuid4().hex}"

    print(f"Add a task: {task_id}, File Path: {saved_paths}", flush=True)

    # 添加到处理队列
    processing_queue.add_task(task_id, saved_paths, llm_model, prompt,
                              whisper_model_size)

    return task_id, {"status": "Joined the queue, please wait..."}


def check_status(task_id: str) -> Tuple[Dict, List, List, gr.Timer]:
    """Checking the Task Status"""
    result = processing_queue.get_result(task_id)

    if result["status"] == "completed":
        # Arrange results for display
        display_result = []
        clip_result = []
        for file_result in result["result"]:
            for seg in file_result["segments"]:
                row = [file_result["filename"],
                       f"{seconds_to_hhmmss(seg['start'])}",
                       f"{seconds_to_hhmmss(seg['end'])}",
                       f"{seconds_to_hhmmss(seg['end'] - seg['start'])}",
                       seg["summary"],
                       ", ".join(seg["tags"]) if isinstance(
                           seg["tags"], list) else seg["tags"]]
                clip_row = row.copy()
                clip_row.insert(0, CHECKBOX_UNCHECKED)  # Add a selection box
                display_result.append(row)
                clip_result.append(clip_row)

        return (
            {"task_id": task_id, "status": "Processing completed",
             "raw_result": result["result"],
             "result": display_result, },
            display_result,
            clip_result,
            gr.Timer(active=False)
        )

    elif result["status"] == "error":
        return (
            {"task_id": task_id,
             "status": f"error: {result.get('error', 'Unknown error')}"},
            [], [], gr.update()
        )
    elif result["status"] == "queued":
        return (
            {"task_id": task_id,
             "status": f"In the queue, There is more{processing_queue.get_queue_size()}Tasks"},
            [], [], gr.update()
        )

    if task_id:
        return (
            {"task_id": task_id, "status": "Processing...",
             "status_info": result.get("status_info", "")},
            [], [], gr.update()
        )
    else:
        return (
            {"task_id": "", "status": ""},
            [], [], gr.update()
        )


def select_clip(segment_selection: List[List], evt: gr.SelectData) -> List[
    List]:
    """Select Clip"""
    selected_row = segment_selection[evt.index[0]]
    # Toggle selection state
    selected_row[0] = CHECKBOX_CHECKED \
        if selected_row[0] == CHECKBOX_UNCHECKED else CHECKBOX_UNCHECKED
    return segment_selection


def clip_and_download(status_display: Dict,
                      segment_selection: List[List], download_mode: str) -> str:
    """Clip and download selected clips"""
    if not status_display or "raw_result" not in status_display:
        raise gr.Error("Invalid processing result")

    # 获取任务ID用于创建唯一目录
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
    if download_mode == "Merge into one file":
        # 检查所有片段格式是否一致
        formats = set()
        for seg in selected_segments:
            filename = seg[1]
            file_ext = file_segments[filename]['ext']
            formats.add(file_ext.lower())

        if len(formats) > 1:
            raise gr.Error(
                "Unable to merge: The selected clip contains multiple formats: " + ", ".join(formats))

    selected_clips = []
    for seg in selected_segments:
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
    if download_mode == "Merge into one file":
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
            print(f"FFmpeg error: {e.stderr.decode('utf-8')}")
            raise gr.Error(f"File merging failed: {str(e)}")

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
        'status': 'Please wait, re-analyzing with new hints...',
    }


def reanalyze_with_prompt(task_id: str, reanalyze_llm_model: str,
                          new_prompt: str) -> Tuple[
    Dict, List[List], List[List]]:
    """Reanalyze using new prompts"""
    if not task_id:
        raise gr.Error("Invalid task ID")
    task_result = processing_queue.get_result(task_id)
    if not task_result or "result" not in task_result:
        raise gr.Error("There is no content to reanalyze")

    if not new_prompt:
        raise gr.Error("Please enter a new analysis prompt")

    if not reanalyze_llm_model:
        raise gr.Error("Please select a large language model")

    try:
        # Reprocess with new prompt
        from modules.llm_processor import LLMProcessor
        llm = LLMProcessor(reanalyze_llm_model)
        updated_results = []

        for file_data in task_result["result"]:
            new_segments = llm.segment_video(
                file_data["align_result"]["segments"], new_prompt)
            updated_results.append({
                "filename": file_data["filename"],
                "filepath": file_data["filepath"],
                "align_result": file_data["align_result"],
                "segments": new_segments
            })

        # Arrange results for display
        display_result = []
        clip_result = []
        for file_result in updated_results:
            for seg in file_result["segments"]:
                row = [file_result["filename"],
                       f"{seconds_to_hhmmss(seg['start'])}",
                       f"{seconds_to_hhmmss(seg['end'])}",
                       f"{seconds_to_hhmmss(seg['end'] - seg['start'])}",
                       seg["summary"],
                       ", ".join(seg["tags"]) if isinstance(
                           seg["tags"], list) else seg["tags"]]
                clip_row = row.copy()
                clip_row.insert(0, CHECKBOX_UNCHECKED)  # Add a selection box
                display_result.append(row)
                clip_result.append(clip_row)

        return ({
                    "task_id": task_id,
                    "status": "Reanalysis completed, please check in analysis results",
                    "result": display_result,
                    "raw_result": updated_results
                }, display_result, clip_result)

    except Exception as e:
        print(f"Reanalysis failed: {str(e)}")
        task_result["status"] = "error"
        task_result["status_info"] = f"The reanalysis was unsuccessful: {str(e)}"
        return task_result, [], []


def create_gradio_interface():
    """Creating the Gradio Interface"""
    with (gr.Blocks(title="Cut", theme=gr.themes.Soft()) as app):
        gr.Markdown("# 🎬 Cut-AI Video Editing Assistant")
        gr.Markdown(
            "Upload a video/audio file containing voice, and AI will automatically recognize the voice content, intelligently segment it, and allow you to enter natural language for retrieval.")

        with gr.Row():
            with gr.Column(scale=2):
                file_upload = gr.Files(
                    label="Upload video/audio files",
                    file_count="multiple"
                )

                with gr.Accordion("Advanced Settings", open=False):
                    llm_model = gr.Dropdown(
                        choices=[model['label'] for model in LLM_MODEL_OPTIONS],
                        value="Qwen3 8B", label="Large Language Model")
                    model_size = gr.Dropdown(
                        choices=["large-v3", "large-v2", "large", "medium",
                                 "small", "base", "tiny"],
                        value=WHISPER_MODEL_SIZE,
                        label="Speech recognition model size"
                    )

                prompt_input = gr.Textbox(
                    label="Custom analysis prompts (optional)",
                    placeholder="Example: Find all the clips about product demos",
                    lines=2
                )
                process_btn = gr.Button("Start processing", variant="primary")

                with gr.Row():
                    status_display = gr.JSON(label="Processing Status")
                    task_id = gr.Textbox(visible=False)

            with gr.Column(scale=3):
                with gr.Tab("Analyze the results"):
                    result_table = gr.Dataframe(
                        headers=["file name", "Start time", "End time", "Duration",
                                 "Summary", "Label"],
                        datatype=["str", "str", "str", "str", "str", "str"],
                        interactive=False,
                        wrap=True
                    )

                with gr.Tab("Reanalysis"):
                    new_prompt = gr.Textbox(
                        label="Enter a new analysis prompt",
                        placeholder="Example: Find all snippets containing technical terms",
                        lines=2
                    )
                    reanalyze_llm_model = gr.Dropdown(
                        choices=[model['label'] for model in LLM_MODEL_OPTIONS],
                        value= "Qwen3 8B", label="Large Language Model")
                    reanalyze_btn = gr.Button("Reanalysis", variant="secondary")

                with gr.Tab("Clipping options"):
                    segment_selection = gr.Dataframe(
                        headers=["file name", "Start time", "End time", "Duration",
                                 "Summary", "Label"],
                        datatype='html',
                        interactive=False,
                        wrap=True,
                        type="array",
                        label="Select the clips you want to keep"
                    )
                    segment_selection.select(select_clip,
                                             inputs=segment_selection,
                                             outputs=segment_selection)
                    # Add download mode selection
                    download_mode = gr.Radio(
                        choices=["Package into zip file", "Merge into one file"],
                        label="How to handle when multiple files are selected",
                        value="Package into zip file"
                    )
                    clip_btn = gr.Button("Editing", variant="primary")
                    download_output = gr.File(label="Download Clip Results")

        # Timer for polling status
        timer = gr.Timer(2, active=False)
        timer.tick(check_status, task_id,
                   outputs=[status_display, result_table, segment_selection,
                            timer])

        # Event Handling
        process_btn.click(
            process_files,
            inputs=[file_upload, llm_model, prompt_input, model_size],
            outputs=[task_id, status_display]
        ).then(
            lambda: gr.Timer(active=True),
            inputs=None,
            outputs=timer,
            show_progress="hidden"
        )

        reanalyze_btn.click(
            start_reanalyze,
            inputs=None,
            outputs=status_display,
        ).then(
            reanalyze_with_prompt,
            inputs=[task_id, reanalyze_llm_model, new_prompt],
            outputs=[status_display, result_table, segment_selection],
            show_progress="hidden"
        )

        clip_btn.click(
            clip_and_download,
            inputs=[status_display, segment_selection, download_mode],
            outputs=download_output
        )

        return app
