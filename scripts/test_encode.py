import sys, os
sys.path.insert(0, os.path.abspath('src'))
from python_cuda_bridge import encode_frames_to_mp4
import numpy as np
frames = [ (np.random.rand(100,100)*255).astype('uint8') for _ in range(20) ]
out = 'test_video.mp4'
import time
start=time.time()
try:
    encode_frames_to_mp4(frames,out,fps=5)
    print('Encoded', out, 'size', os.path.getsize(out),'time',time.time()-start)
except Exception as e:
    print('Encoding failed:', e)
