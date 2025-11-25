#!/usr/bin/env python3
"""
Video Acceleration Engine - GPU-accelerated video encoding
Supports H.264, H.265, VP9 with optional CUDA/HW acceleration
"""

import os
import cv2
import numpy as np
import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class VideoConfig:
    """Video encoding configuration"""
    codec: str = "h264"  # h264, h265, vp9
    bitrate: str = "5000k"  # 1000k, 5000k, 10000k
    preset: str = "fast"  # ultrafast, fast, medium, slow
    gpu_enabled: bool = True
    crf: int = 23  # Quality (0-51, lower=better, 23=default)
    fps: int = 30
    width: Optional[int] = None
    height: Optional[int] = None
    scale_filter: str = "lanczos"  # lanczos, bicubic, bilinear
    
    def get_ffmpeg_codec(self) -> str:
        """Get FFmpeg codec name for encoding"""
        if self.gpu_enabled:
            # NVIDIA hardware acceleration
            if self.codec == "h264":
                return "h264_nvenc"
            elif self.codec == "h265":
                return "hevc_nvenc"
            elif self.codec == "vp9":
                return "vp9"  # VP9 has limited GPU support
        
        # Fallback to software encoding
        codec_map = {
            "h264": "libx264",
            "h265": "libx265",
            "vp9": "libvpx-vp9"
        }
        return codec_map.get(self.codec, "libx264")

class GPUVideoAccelerator:
    """GPU-accelerated video encoding engine"""
    
    def __init__(self, config: VideoConfig = None):
        self.config = config or VideoConfig()
        self.gpu_available = self._check_gpu_availability()
        
        if not self.gpu_available and self.config.gpu_enabled:
            logger.warning("GPU not available, falling back to CPU encoding")
            self.config.gpu_enabled = False
    
    def _check_gpu_availability(self) -> bool:
        """Check if NVIDIA GPU is available for encoding"""
        try:
            # Try to detect NVIDIA GPU via ffmpeg
            result = subprocess.run(
                ["ffmpeg", "-hide_banner", "-hwaccels"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            has_cuda = "cuda" in result.stdout.lower() or "nvenc" in result.stdout.lower()
            has_cuvid = "cuvid" in result.stdout.lower()
            
            if has_cuda or has_cuvid:
                logger.info("NVIDIA CUDA GPU detected for hardware acceleration")
                return True
            
            # Try OpenCL fallback
            has_opencl = "opencl" in result.stdout.lower()
            if has_opencl:
                logger.info("OpenCL GPU detected")
                return True
                
        except Exception as e:
            logger.warning(f"Could not detect GPU: {e}")
        
        return False
    
    def encode_from_frames(self, 
                          frame_iterator,
                          output_path: str,
                          width: Optional[int] = None,
                          height: Optional[int] = None) -> bool:
        """
        Encode video from frame iterator using FFmpeg with GPU acceleration
        
        Args:
            frame_iterator: Iterator yielding numpy arrays (BGR)
            output_path: Path to output video file
            width: Output video width
            height: Output video height
        
        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting video encoding to {output_path}")
        logger.info(f"Config: {self.config.codec} @ {self.config.bitrate}, GPU={self.config.gpu_enabled}")
        
        # Get first frame to determine dimensions
        try:
            first_frame = next(frame_iterator)
        except StopIteration:
            logger.error("Frame iterator is empty")
            return False
        
        # Determine dimensions
        h, w = first_frame.shape[:2]
        if width and height:
            self.config.width = width
            self.config.height = height
        else:
            self.config.width = w
            self.config.height = h
        
        # Setup FFmpeg command
        codec = self.config.get_ffmpeg_codec()
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{self.config.width}x{self.config.height}",
            "-pix_fmt", "bgr24",
            "-r", str(self.config.fps),
            "-i", "-",  # Read from stdin
        ]
        
        # Add codec-specific options
        if self.config.gpu_enabled and codec in ["h264_nvenc", "hevc_nvenc"]:
            ffmpeg_cmd.extend([
                "-c:v", codec,
                "-preset", self.config.preset,  # fast, medium, slow for NVENC
                "-b:v", self.config.bitrate,
            ])
        else:
            # Software encoding options
            ffmpeg_cmd.extend([
                "-c:v", codec,
                "-preset", self.config.preset,
                "-crf", str(self.config.crf),
            ])
        
        # Add output format options
        ffmpeg_cmd.extend([
            "-pix_fmt", "yuv420p",  # Required for H.264/H.265 compatibility
            "-movflags", "faststart",  # Enable streaming
            str(output_path)
        ])
        
        logger.info(f"FFmpeg command: {' '.join(ffmpeg_cmd)}")
        
        # Start FFmpeg process
        try:
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False
            )
        except FileNotFoundError:
            logger.error("FFmpeg not found. Install with: conda install -c conda-forge ffmpeg")
            return False
        
        # Write frames to FFmpeg stdin
        frame_count = 0
        try:
            # Write first frame (already extracted)
            if first_frame.shape[2] == 4:  # RGBA
                frame_bgr = cv2.cvtColor(first_frame, cv2.COLOR_RGBA2BGR)
            elif first_frame.shape[2] == 3:  # BGR
                frame_bgr = first_frame
            else:  # Grayscale
                frame_bgr = cv2.cvtColor(first_frame, cv2.COLOR_GRAY2BGR)
            
            # Resize if needed
            if frame_bgr.shape[:2] != (self.config.height, self.config.width):
                frame_bgr = cv2.resize(
                    frame_bgr,
                    (self.config.width, self.config.height),
                    interpolation=self._get_interpolation()
                )
            
            process.stdin.write(frame_bgr.tobytes())
            frame_count += 1
            
            # Write remaining frames
            for frame in frame_iterator:
                if frame.shape[2] == 4:  # RGBA
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
                elif frame.shape[2] == 3:  # BGR
                    frame_bgr = frame
                else:  # Grayscale
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                
                # Resize if needed
                if frame_bgr.shape[:2] != (self.config.height, self.config.width):
                    frame_bgr = cv2.resize(
                        frame_bgr,
                        (self.config.width, self.config.height),
                        interpolation=self._get_interpolation()
                    )
                
                process.stdin.write(frame_bgr.tobytes())
                frame_count += 1
                
                # Log progress every 100 frames
                if frame_count % 100 == 0:
                    logger.info(f"Encoded {frame_count} frames...")
            
            process.stdin.close()
            
        except Exception as e:
            logger.error(f"Error writing frames: {e}")
            process.terminate()
            return False
        
        # Wait for process completion
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            logger.error(f"FFmpeg error: {stderr.decode('utf-8', errors='ignore')}")
            return False
        
        logger.info(f"Video encoding complete! {frame_count} frames written")
        
        # Verify output file
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            logger.info(f"Output file size: {file_size_mb:.2f} MB")
            return True
        else:
            logger.error("Output file not created or is empty")
            return False
    
    def encode_from_images(self, image_paths: List[str], output_path: str) -> bool:
        """Encode video from list of image files"""
        def image_generator():
            for img_path in image_paths:
                img = cv2.imread(str(img_path))
                if img is None:
                    logger.warning(f"Could not read image: {img_path}")
                    continue
                yield img
        
        return self.encode_from_frames(image_generator(), output_path)
    
    def transcode_video(self, input_path: str, output_path: str) -> bool:
        """Transcode video with GPU acceleration"""
        logger.info(f"Transcoding {input_path} to {output_path}")
        
        codec = self.config.get_ffmpeg_codec()
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", str(input_path),
            "-c:v", codec,
            "-preset", self.config.preset,
            "-crf", str(self.config.crf),
            "-c:a", "aac",
            "-b:a", "128k",
            "-y",
            str(output_path)
        ]
        
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                logger.info("Transcoding complete!")
                return True
            else:
                logger.error(f"Transcoding failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Transcoding error: {e}")
            return False
    
    def _get_interpolation(self):
        """Get OpenCV interpolation method"""
        filters = {
            "lanczos": cv2.INTER_LANCZOS4,
            "bicubic": cv2.INTER_CUBIC,
            "bilinear": cv2.INTER_LINEAR,
            "nearest": cv2.INTER_NEAREST
        }
        return filters.get(self.config.scale_filter, cv2.INTER_LANCZOS4)
    
    def get_stats(self) -> dict:
        """Get acceleration statistics"""
        return {
            "gpu_available": self.gpu_available,
            "gpu_enabled": self.config.gpu_enabled,
            "codec": self.config.codec,
            "preset": self.config.preset,
            "bitrate": self.config.bitrate,
            "fps": self.config.fps
        }


if __name__ == "__main__":
    # Example usage
    config = VideoConfig(
        codec="h264",
        preset="fast",
        gpu_enabled=True,
        bitrate="5000k"
    )
    
    accelerator = GPUVideoAccelerator(config)
    print("Video Acceleration Engine Ready")
    print(accelerator.get_stats())
