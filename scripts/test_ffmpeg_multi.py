import shutil, subprocess
import numpy as np

ffmpeg_exe = shutil.which("ffmpeg")
cmd = [
    ffmpeg_exe,
    "-y",
    "-f",
    "rawvideo",
    "-vcodec",
    "rawvideo",
    "-pix_fmt",
    "rgb24",
    "-s",
    "100x100",
    "-r",
    "5",
    "-i",
    "-",
    "-an",
    "-vcodec",
    "libx264",
    "-pix_fmt",
    "yuv420p",
    "test_video_multi.mp4",
]
print("Running:", " ".join(cmd))
proc = subprocess.Popen(
    cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
)
try:
    for i in range(20):
        frame = (np.random.rand(100, 100) * 255).astype("uint8")
        rgb = np.stack([frame, frame, frame], axis=-1)
        proc.stdin.write(rgb.tobytes())
    proc.stdin.close()
    out, err = proc.communicate(timeout=30)
    print("Return", proc.returncode)
    print("stderr:", err.decode("utf-8", errors="ignore")[:1000])
except Exception as e:
    print("Exception", type(e), e)
    try:
        proc.kill()
    except Exception:
        pass

print("done")
