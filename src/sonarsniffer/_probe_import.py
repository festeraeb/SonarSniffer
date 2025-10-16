import sys, traceback, importlib.util, pathlib
p = pathlib.Path("video_exporter.py").resolve()
print("Trying:", p)
try:
    spec = importlib.util.spec_from_file_location("video_exporter_local", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    print("OK ->", m.__file__)
except Exception:
    print("FAILED loading video_exporter.py:\n")
    traceback.print_exc()
    sys.exit(1)
