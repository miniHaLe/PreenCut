import os
import subprocess
from config import TEMP_FOLDER
from typing import List, Dict
from utils import generate_safe_filename


class VideoProcessor:
    @staticmethod
    def extract_audio(video_path: str, task_id: str) -> str:
        """Extract audio from video"""

        task_temp_dir = os.path.join(TEMP_FOLDER, task_id)
        os.makedirs(task_temp_dir, exist_ok=True)
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        audio_path = os.path.join(task_temp_dir, f"{base_name}.wav")

        cmd = [
            'ffmpeg', '-i', video_path,
            '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
            '-y', audio_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL)
        return audio_path

    @staticmethod
    def clip_video(input_path: str, segments: List[Dict], output_folder: str,
                   ext: str) -> List[str]:
        """Clip videos by segment"""
        # Create a list of temporary files
        clip_list = []
        # Generate safe file names
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        safe_filename = generate_safe_filename(base_name, max_length=100)

        for i, seg in enumerate(segments):
            clip_path = os.path.join(output_folder,
                                     f"{safe_filename}_clip_{i}{ext}")

            cmd = [
                'ffmpeg', '-i', input_path,
                '-ss', str(seg['start']),
                '-to', str(seg['end']),
                '-c:v', 'libx264',  # Video Encoder
                '-c:a', 'copy',  # Audio Direct Copy
                '-avoid_negative_ts', 'make_zero',
                '-y', clip_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"FFmpeg error: {result.stderr}")
                raise RuntimeError(f"Video editing failed: {result.stderr}")
            clip_list.append(clip_path)

        return clip_list
