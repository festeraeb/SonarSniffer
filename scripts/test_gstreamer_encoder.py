import os, sys
sys.path.insert(0, os.path.abspath('src'))
from sonarsniffer import gstreamer_bridge
import numpy as np

# Quick test: build a small 200x64 video of random noise. An env var GST_TEST_ENCODER can force the encoder element (e.g., 'x264enc')
H, W = 64, 200
frames = [ (np.random.rand(H,W)*255).astype('uint8') for _ in range(30) ]
out = 'test_gst_out.mp4'

encoder = os.environ.get('GST_TEST_ENCODER')
# First try normal encode (streaming). If GST_TEST_FORCE_FALLBACK=yes, simulate a failing encoder by forcing a bad encoder name.
if os.environ.get('GST_TEST_FORCE_FALLBACK', '').lower() in ('1', 'true', 'yes'):
    encoder = 'nonexistent_encoder_element'

try:
    # If GST_TEST_USE_IMAGE_SEQ=1, force the image-sequence code path
    if os.environ.get('GST_TEST_USE_IMAGE_SEQ', '').lower() in ('1', 'true', 'yes'):
        # Materialize frames list and call image-sequence helper directly
        try:
            fl = list(frames)
        except Exception:
            fl = frames
        gstreamer_bridge._encode_via_gst_image_sequence(fl, out, fps=5, width=W, height=H, encoder=encoder)
        print('Encoded via gst image-sequence mode to', out)
    else:
        # Prefer the higher-level function that includes fallback logic
        gstreamer_bridge.encode_frames_with_fallback(frames, out, fps=5, width=W, height=H, encoder=encoder)
        print('Encoded (or fallback used) via gstreamer bridge to', out)
except Exception as e:
    print('GStreamer encoder test failed:', e)
    print('Ensure gst_encoder binary is built and GStreamer plugins are installed, and ffmpeg is available for fallback.')
    if encoder:
        print('Attempted encoder:', encoder)
    else:
        print('No encoder override provided. Use GST_TEST_ENCODER=\'x264enc\' to force software encoder or GST_TEST_FORCE_FALLBACK=1 to force fallback test.')
