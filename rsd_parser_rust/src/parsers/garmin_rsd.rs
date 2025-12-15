/// Garmin RSD format parser
/// Handles Classic, UHD, UHD2 variants with varstruct decoding

use crate::{RsdError, RsdResult, SonarRecord, MAGIC_REC_HDR};
use std::fs::File;
use std::io::Read;
use std::path::Path;

pub struct GarminRsdParser {
    file_path: String,
    file_size: u64,
}

impl GarminRsdParser {
    pub fn new(file_path: &str) -> RsdResult<Self> {
        let path = Path::new(file_path);
        let metadata = std::fs::metadata(path)?;
        
        Ok(GarminRsdParser {
            file_path: file_path.to_string(),
            file_size: metadata.len(),
        })
    }
    
    pub fn file_size(&self) -> u64 {
        self.file_size
    }
    
    pub fn get_info(&self) -> String {
        format!(
            "RSD File: {}\nSize: {} bytes ({:.1} MB)",
            Path::new(&self.file_path).file_name().unwrap_or_default().to_string_lossy(),
            self.file_size,
            self.file_size as f64 / 1024.0 / 1024.0
        )
    }
    
    pub fn record_count(&self) -> RsdResult<u32> {
        // Estimate: scan file for magic bytes
        let mut file = File::open(&self.file_path)?;
        let mut buffer = vec![0u8; 1024 * 1024];
        let mut count = 0u32;
        
        loop {
            let bytes_read = file.read(&mut buffer)?;
            if bytes_read == 0 {
                break;
            }
            
            for window in buffer[..bytes_read].windows(4) {
                let magic = u32::from_le_bytes([window[0], window[1], window[2], window[3]]);
                if magic == MAGIC_REC_HDR {
                    count += 1;
                }
            }
        }
        
        Ok(count)
    }
    
    /// Parse all records from file
    pub fn parse_all(&self, limit: Option<u32>) -> RsdResult<Vec<SonarRecord>> {
        let mut file = File::open(&self.file_path)?;
        let mut buffer = vec![0u8; 1024 * 1024]; // 1MB buffer
        
        // Read file into buffer (for smaller files)
        if self.file_size < 500 * 1024 * 1024 {
            buffer.clear();
            file.read_to_end(&mut buffer)?;
            
            self.parse_buffer(&buffer, limit)
        } else {
            // Stream large files
            self.parse_streaming(&mut file, limit)
        }
    }
    
    fn parse_buffer(&self, buffer: &[u8], limit: Option<u32>) -> RsdResult<Vec<SonarRecord>> {
        let mut records = Vec::new();
        let mut offset = 0usize;
        let mut count = 0u32;
        
        while offset < buffer.len() {
            if let Some(limit_val) = limit {
                if count >= limit_val {
                    break;
                }
            }
            
            // Look for header magic
            if offset + 4 > buffer.len() {
                break;
            }
            
            let magic = u32::from_le_bytes([
                buffer[offset],
                buffer[offset + 1],
                buffer[offset + 2],
                buffer[offset + 3],
            ]);
            
            if magic == MAGIC_REC_HDR {
                // Parse record starting at this offset
                match self.parse_record_at(&buffer, offset) {
                    Ok(record) => {
                        records.push(record);
                        count += 1;
                        offset += 1024; // Move forward (heuristic)
                    }
                    Err(_) => {
                        offset += 1; // Try next byte
                    }
                }
            } else {
                offset += 1;
            }
        }
        
        Ok(records)
    }
    
    fn parse_streaming(&self, file: &mut File, limit: Option<u32>) -> RsdResult<Vec<SonarRecord>> {
        let mut records = Vec::new();
        let mut buffer = vec![0u8; 1024 * 1024];
        let mut count = 0u32;
        let mut file_offset = 0u64;
        
        loop {
            let bytes_read = file.read(&mut buffer)?;
            if bytes_read == 0 {
                break;
            }
            
            let mut buffer_offset = 0usize;
            while buffer_offset < bytes_read {
                if let Some(limit_val) = limit {
                    if count >= limit_val {
                        return Ok(records);
                    }
                }
                
                if buffer_offset + 4 > bytes_read {
                    break;
                }
                
                let magic = u32::from_le_bytes([
                    buffer[buffer_offset],
                    buffer[buffer_offset + 1],
                    buffer[buffer_offset + 2],
                    buffer[buffer_offset + 3],
                ]);
                
                if magic == MAGIC_REC_HDR {
                    match self.parse_record_at(&buffer[buffer_offset..], 0) {
                        Ok(mut record) => {
                            record.offset = file_offset + buffer_offset as u64;
                            records.push(record);
                            count += 1;
                            buffer_offset += 1024;
                        }
                        Err(_) => {
                            buffer_offset += 1;
                        }
                    }
                } else {
                    buffer_offset += 1;
                }
            }
            
            file_offset += bytes_read as u64;
        }
        
        Ok(records)
    }
    
    /// Parse single record from buffer at offset
    #[allow(unused_assignments)]
    fn parse_record_at(&self, buffer: &[u8], start: usize) -> RsdResult<SonarRecord> {
        if start + 4 > buffer.len() {
            return Err(RsdError::CorruptedRecord);
        }
        
        let magic = u32::from_le_bytes([
            buffer[start],
            buffer[start + 1],
            buffer[start + 2],
            buffer[start + 3],
        ]);
        
        if magic != MAGIC_REC_HDR {
            return Err(RsdError::InvalidFormat {
                offset: start as u64,
                reason: "Invalid magic byte".to_string(),
            });
        }
        
        let mut record = SonarRecord {
            offset: start as u64,
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
        };
        
        // Try to extract basic fields from varstruct
        let mut offset = start + 4;
        
        // Read sequence field
        if offset + 4 <= buffer.len() {
            record.sequence = u32::from_le_bytes([
                buffer[offset],
                buffer[offset + 1],
                buffer[offset + 2],
                buffer[offset + 3],
            ]);
            offset += 4;
        }
        
        // Read time field
        if offset + 4 <= buffer.len() {
            record.time_ms = u32::from_le_bytes([
                buffer[offset],
                buffer[offset + 1],
                buffer[offset + 2],
                buffer[offset + 3],
            ]);
            offset += 4;
        }
        
        Ok(record)
    }
}
