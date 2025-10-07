# 1. Create the conda environment
conda create -n cesarops python=3.9 -y
conda activate cesarops

# 2. Install all dependencies via conda (much more reliable)
conda install -c conda-forge opendrift pandas numpy scipy matplotlib netcdf4 xarray requests pyyaml python-dateutil scikit-learn joblib shapely pyproj cartopy -y

# 3. Install remaining via pip
pip install simplekml

# 4. Copy the fixed sarops.py and requirements.txt to your directory
# 5. Test: python -c "import opendrift; print('Success!')"