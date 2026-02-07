import importlib, json, sys, os
# Ensure repository root is on sys.path so 'src' package can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
m = importlib.import_module('src.sonarsniffer')
print(json.dumps({
    'INCREMENTAL_LOADING_AVAILABLE': bool(getattr(m,'INCREMENTAL_LOADING_AVAILABLE',False)),
    'ML_PIPELINE_AVAILABLE': bool(getattr(m,'ML_PIPELINE_AVAILABLE',False)),
    'GEOSPATIAL_EXPORT_AVAILABLE': bool(getattr(m,'GEOSPATIAL_EXPORT_AVAILABLE',False)),
    'VERSION': getattr(m, '__version__', None)
}, indent=2))
