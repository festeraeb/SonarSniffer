import sys

sys.path.insert(0, "src")
import traceback

try:
    import numpy as np

    print("numpy ok", np.__version__)
except Exception as e:
    print("numpy import failed")
    traceback.print_exc()
