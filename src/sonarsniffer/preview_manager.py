#!/usr/bin/env python3
"""Preview manager for RSD Studio."""
from typing import Optional, Tuple, List, Callable
import threading
import queue
import numpy as np
from PIL import Image
from pathlib import Path
from color_manager import ColorManager

class PreviewManager:
    """Handles real-time preview generation and updates."""
    
    def __init__(self, update_callback: Optional[Callable] = None):
        self.color_manager = ColorManager()
        self._update_callback = update_callback
        self._preview_queue = queue.Queue()
        self._preview_thread = None
        self._running = False
        self._current_paths: List[str] = []
        self._current_config = {}
    
    def start(self):
        """Start preview processing thread."""
        if self._preview_thread is not None:
            return
            
        self._running = True
        self._preview_thread = threading.Thread(target=self._preview_loop, daemon=True)
        self._preview_thread.start()
    
    def stop(self):
        """Stop preview processing."""
        self._running = False
        if self._preview_thread:
            self._preview_thread.join()
            self._preview_thread = None
    
    def update_config(self, cfg: dict):
        """Update preview configuration."""
        self._current_config = cfg.copy()
        self._trigger_update()
    
    def update_paths(self, paths: List[str]):
        """Update image paths for preview."""
        self._current_paths = paths.copy()
        self._trigger_update()
    
    def _trigger_update(self):
        """Queue a preview update."""
        try:
            self._preview_queue.put_nowait(("update", None))
        except queue.Full:
            pass # Skip if queue is full
    
    def _preview_loop(self):
        """Main preview processing loop."""
        while self._running:
            try:
                cmd, data = self._preview_queue.get(timeout=0.1)
                if cmd == "update":
                    self._generate_preview()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Preview error: {str(e)}")
    
    def _generate_preview(self):
        """Generate preview from current paths and config."""
        if not self._current_paths:
            return
            
        try:
            # Load first image to get dimensions
            img0 = np.array(Image.open(self._current_paths[0]))
            h, w = img0.shape[:2]
            
            # Apply color map
            cmap = self._current_config.get("COLORMAP", "grayscale")
            preview = self.color_manager.apply(img0, cmap)
            
            # Handle preview mode
            mode = self._current_config.get("PREVIEW_MODE", "auto")
            if mode == "both" and len(self._current_paths) > 1:
                img1 = np.array(Image.open(self._current_paths[1]))
                preview1 = self.color_manager.apply(img1, cmap)
                
                # Stack side by side
                preview = np.hstack([preview, preview1])
                
                # Add seam indicator if requested
                if self._current_config.get("SHOW_SEAM", True):
                    preview[:, w-1:w+1] = [255, 0, 0]  # Red line
            
            # Scale preview if height specified
            target_h = self._current_config.get("PREVIEW_HEIGHT")
            if target_h:
                target_h = int(target_h)
                if target_h != h:
                    scale = target_h / h
                    new_w = int(preview.shape[1] * scale)
                    preview = Image.fromarray(preview).resize((new_w, target_h), Image.Resampling.LANCZOS)
                    preview = np.array(preview)
            
            # Notify callback
            if self._update_callback:
                self._update_callback(preview)
                
        except Exception as e:
            print(f"Preview generation error: {str(e)}")
    
    def get_available_colormaps(self) -> List[str]:
        """Get list of available colormaps."""
        return self.color_manager.get_colormap_names()