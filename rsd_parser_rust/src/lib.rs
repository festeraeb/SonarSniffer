use pyo3::prelude::*;
use std::io;
use serde::{Deserialize, Serialize};
use thiserror::Error;
use pyo3::types::PyModule;
use pyo3::Bound;

/// RSD parsing errors
#[derive(Error, Debug)]
pub enum RsdError {
    #[error("IO error: {0}")]
    Io(#[from] io::Error),
    
    #[error("Invalid RSD format at offset {offset}: {reason}")]
    InvalidFormat { offset: u64, reason: String },
    
    #[error("CRC validation failed")]
    CrcValidationFailed,
    
    #[error("Corrupted record")]
    CorruptedRecord,
}

pub type RsdResult<T> = Result<T, RsdError>;

/// Magic bytes for RSD record header/trailer
pub const MAGIC_REC_HDR: u32 = 0xB7E9DA86;
pub const MAGIC_REC_TRL: u32 = 0xC4D2B1A5;

/// Parsed sonar record from RSD file
#[derive(Debug, Clone, Serialize, Deserialize)]
#[pyclass]
pub struct SonarRecord {
    #[pyo3(get)]
    pub offset: u64,
    #[pyo3(get)]
    pub sequence: u32,
    #[pyo3(get)]
    pub time_ms: u32,
    #[pyo3(get)]
    pub channel_id: Option<u32>,
    #[pyo3(get)]
    pub latitude: Option<f64>,
    #[pyo3(get)]
    pub longitude: Option<f64>,
    #[pyo3(get)]
    pub depth_m: Option<f64>,
    #[pyo3(get)]
    pub water_temp_c: Option<f32>,
    #[pyo3(get)]
    pub water_temp_f: Option<f32>,
    #[pyo3(get)]
    pub pitch_deg: Option<f32>,
    #[pyo3(get)]
    pub roll_deg: Option<f32>,
    #[pyo3(get)]
    pub beam_angle_deg: Option<f32>,
    #[pyo3(get)]
    pub gps_speed_knots: Option<f32>,
    #[pyo3(get)]
    pub gps_heading_deg: Option<f32>,
    #[pyo3(get)]
    pub sample_count: Option<u32>,
    #[pyo3(get)]
    pub sonar_offset: Option<u32>,
    #[pyo3(get)]
    pub sonar_size: Option<u32>,
}

#[pymethods]
impl SonarRecord {
    #[new]
    fn new() -> Self {
        SonarRecord {
            offset: 0,
            sequence: 0,
            time_ms: 0,
            channel_id: None,
            latitude: None,
            longitude: None,
            depth_m: None,
            water_temp_c: None,
            water_temp_f: None,
            pitch_deg: None,
            roll_deg: None,
            beam_angle_deg: None,
            gps_speed_knots: None,
            gps_heading_deg: None,
            sample_count: None,
            sonar_offset: None,
            sonar_size: None,
        }
    }
    
    fn __repr__(&self) -> String {
        format!(
            "SonarRecord(seq={}, time={}, lat={:?}, lon={:?}, depth={:?})",
            self.sequence, self.time_ms, self.latitude, self.longitude, self.depth_m
        )
    }
}

mod parsers;
use parsers::garmin_rsd::GarminRsdParser;

/// Main RSD parser exposed to Python
#[pyclass]
pub struct RsdParser {
    parser: GarminRsdParser,
}

#[pymethods]
impl RsdParser {
    #[new]
    fn new(file_path: String) -> PyResult<Self> {
        let parser = GarminRsdParser::new(&file_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
        
        Ok(RsdParser { parser })
    }
    
    /// Parse all records from RSD file
    fn parse_all(&self, limit: Option<u32>) -> PyResult<Vec<SonarRecord>> {
        self.parser
            .parse_all(limit)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }
    
    /// Parse and yield records as iterator (returns Vec for simplicity)
    fn parse(&self, limit: Option<u32>) -> PyResult<Vec<SonarRecord>> {
        self.parse_all(limit)
    }
    
    /// Get file metadata
    fn get_info(&self) -> PyResult<String> {
        let info = self.parser.get_info();
        Ok(info)
    }
    
    /// Get file size in bytes
    fn file_size(&self) -> u64 {
        self.parser.file_size()
    }
    
    /// Get record count
    fn record_count(&self) -> PyResult<u32> {
        self.parser
            .record_count()
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))
    }
}

/// Python module definition
#[pymodule]
fn rsd_parser_rust(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<SonarRecord>()?;
    m.add_class::<RsdParser>()?;
    
    m.add_function(pyo3::wrap_pyfunction!(parse_rsd_file, m)?)?;
    m.add_function(pyo3::wrap_pyfunction!(parse_rsd_records, m)?)?;
    
    Ok(())
}

/// Standalone function: parse RSD file and return all records
#[pyfunction]
fn parse_rsd_file(file_path: String, limit: Option<u32>) -> PyResult<Vec<SonarRecord>> {
    let parser = RsdParser::new(file_path)?;
    parser.parse_all(limit)
}

/// Standalone function: parse RSD records (alias for parse_rsd_file)
#[pyfunction]
fn parse_rsd_records(file_path: String, limit: Option<u32>) -> PyResult<Vec<SonarRecord>> {
    parse_rsd_file(file_path, limit)
}
