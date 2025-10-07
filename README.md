# CESAROPS - Comprehensive Environmental SAR Operations Platform

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![OpenDrift](https://img.shields.io/badge/OpenDrift-1.9+-orange.svg)](https://opendrift.github.io/)

CESAROPS is a comprehensive Search and Rescue (SAR) drift modeling system specifically designed for the Great Lakes region. It combines OpenDrift Lagrangian particle tracking with machine learning enhancements to provide accurate drift predictions for maritime search operations.

## 🌊 **Key Features**

### **Core Functionality**
- **Real-time Drift Modeling**: Uses OpenDrift for accurate Lagrangian particle tracking
- **Great Lakes Focus**: Optimized for Lake Michigan, Erie, Huron, Ontario, and Superior
- **Multi-source Data Integration**: Combines currents, weather, water levels, and stream data
- **Offline Capability**: Local database storage for offline SAR operations

### **Machine Learning Enhancements** ⭐ **NEW**
- **Buoy Drift Analysis**: Historical buoy track collection and analysis
- **ML Correction Models**: Machine learning algorithms to improve drift predictions
- **SAR Literature Database**: Integrated research and drift parameter references
- **Case Analysis**: Specific drift analysis for missing person cases

### **Data Sources**
- **NOAA NDBC**: Real-time and historical buoy data
- **GLERL ERDDAP**: Great Lakes current and water level data
- **NOAA CO-OPS**: Water level stations
- **NWS Weather**: Wind and weather forecasts
- **USGS Streams**: River and stream flow data

## 🚀 **Installation**

### **Prerequisites**
- Python 3.8 or higher
- Git

### **Quick Install**
```bash
# Clone the repository
git clone https://github.com/festeraeb/CESARops.git
cd CESARops

# Install dependencies
pip install -r requirements.txt
```

### **Dependencies**
- `opendrift` - Core drift modeling engine
- `xarray` - NetCDF data handling
- `pandas` - Data analysis
- `numpy` - Numerical computing
- `matplotlib` - Visualization
- `requests` - API data fetching
- `beautifulsoup4` - Web scraping for buoy specs
- `scikit-learn` - Machine learning
- `joblib` - Model serialization

## 📖 **Usage**

### **Basic Operation**
```python
# Start the GUI application
python sarops.py

# Or run console mode
python cesarops.py
```

### **ML Enhancement Testing**
```python
# Run the ML enhancement test suite
python test_ml_enhancements.py

# Update all data sources including ML training data
python -c "from sarops import auto_update_all_data; auto_update_all_data()"
```

### **API Usage**
```python
from sarops import (
    fetch_buoy_specifications,
    analyze_charlie_brown_case,
    train_drift_correction_model
)

# Fetch buoy specifications
fetch_buoy_specifications()

# Analyze a specific case
analysis = analyze_charlie_brown_case()
print(f"Drift probability: {analysis['drift_probability']}")
```

## 🗂️ **Project Structure**

```
CESARops/
├── sarops.py              # Main GUI application
├── cesarops.py            # Simplified simulation script
├── test_ml_enhancements.py # ML enhancement tests
├── requirements.txt        # Python dependencies
├── config.yaml            # Configuration file
├── drift_objects.db       # SQLite database
├── README.md              # This file
├── .gitignore            # Git ignore rules
├── data/                  # NetCDF data files
├── outputs/               # Simulation results
├── models/                # ML models
└── logs/                  # Application logs
```

## 🔬 **Machine Learning Features**

### **Drift Correction Model**
- Trains on historical buoy tracks vs. simulated drift
- Corrects OpenDrift predictions in real-time
- Improves accuracy for SAR operations

### **Training Data Pipeline**
- Automatic collection of environmental conditions
- Buoy track correlation with weather/currents
- Continuous learning from new data

### **SAR Literature Integration**
- Automated research paper collection
- Drift parameter references
- Expandable knowledge base

## 📊 **Example: Charlie Brown Case Analysis**

```python
from sarops import analyze_charlie_brown_case

# Analyze the Milwaukee to South Haven case
analysis = analyze_charlie_brown_case()

print(f"Time in water: {analysis['time_in_water']:.1f} hours")
print(f"Distance traveled: {analysis['distance_traveled']:.2f} nm")
print(f"Drift probability: {analysis['drift_probability']}")
# Output: Time in water: 18.0 hours
#         Distance traveled: 81.29 nm
#         Drift probability: Medium
```

## 🛠️ **Configuration**

Edit `config.yaml` to customize:
- Data source URLs
- Default simulation parameters
- Great Lakes bounding boxes
- GUI settings

## 🤝 **Contributing**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 **Acknowledgments**

- **OpenDrift**: Core drift modeling framework
- **NOAA/GLERL**: Great Lakes environmental data
- **US Coast Guard**: SAR operational guidance
- **NDBC**: Buoy data and specifications

## 📞 **Support**

For questions or issues:
- Open an issue on GitHub
- Check the logs in the `logs/` directory
- Review the test suite output

---

**CESAROPS v2.0** - Enhanced with Machine Learning for Improved SAR Drift Predictions