use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::State;
use uuid::Uuid;

mod db;
mod settings;
mod telemetry;
mod video_processor;

use db::{BenchmarkRecord, Database, ErrorReport, JobMetric};
use settings::SettingsManager;
use telemetry::TelemetryManager;
use video_processor::VideoProcessor;

/// Application state
pub struct AppState {
    pub db: Mutex<Database>,
    pub telemetry: Mutex<TelemetryManager>,
    pub settings: Mutex<SettingsManager>,
    pub processor: Mutex<VideoProcessor>,
}

/// Error response
#[derive(Serialize)]
pub struct ErrorResponse {
    pub error: String,
    pub details: Option<String>,
}

impl ErrorResponse {
    pub fn new(error: &str, details: Option<&str>) -> Self {
        Self {
            error: error.to_string(),
            details: details.map(|s| s.to_string()),
        }
    }
}

/// Process video command
#[derive(Deserialize)]
pub struct ProcessVideoRequest {
    pub input_path: String,
    pub output_path: String,
    pub parser: String,  // "rust" or "python"
    pub encoder: String, // "gstreamer" or "ffmpeg"
    pub settings: Option<serde_json::Value>,
}

/// Get dashboard data command
#[derive(Serialize)]
pub struct DashboardData {
    pub total_errors: u32,
    pub critical_errors: u32,
    pub total_jobs: u32,
    pub successful_jobs: u32,
    pub failed_jobs: u32,
    pub total_records_processed: u64,
    pub parsers_used: serde_json::Value,
    pub encoders_used: serde_json::Value,
    pub benchmarks: serde_json::Value,
}

// Tauri commands

#[tauri::command]
pub fn process_video(
    request: ProcessVideoRequest,
    state: State<AppState>,
) -> Result<serde_json::Value, ErrorResponse> {
    let job_id = Uuid::new_v4().to_string();
    let start_time = Utc::now();

    // Record job start
    let mut db = state.db.lock().unwrap();
    db.insert_job_metric(JobMetric {
        job_id: job_id.clone(),
        timestamp: start_time.to_rfc3339(),
        status: "running".to_string(),
        records_processed: None,
        duration_ms: None,
        parser_used: request.parser.clone(),
        encoder_used: request.encoder.clone(),
        video_resolution: None,
        output_file_size: None,
        success: false,
        error_message: None,
    })
    .map_err(|e| ErrorResponse::new("Failed to record job", Some(&e.to_string())))?;

    drop(db);

    // Process video
    let processor = state.processor.lock().unwrap();
    match processor.process(
        &request.input_path,
        &request.output_path,
        &request.parser,
        &request.encoder,
    ) {
        Ok(result) => {
            let duration = Utc::now().signed_duration_since(start_time);
            let mut db = state.db.lock().unwrap();

            // Update job metric
            db.update_job_metric(
                &job_id,
                result.records_processed as i32,
                duration.num_milliseconds() as i32,
                "completed".to_string(),
                true,
                None,
            )
            .ok();

            Ok(serde_json::json!({
                "job_id": job_id,
                "status": "success",
                "records_processed": result.records_processed,
                "duration_ms": duration.num_milliseconds(),
            }))
        }
        Err(e) => {
            let mut db = state.db.lock().unwrap();

            // Record error
            db.insert_error_report(ErrorReport {
                timestamp: Utc::now().to_rfc3339(),
                error_type: "processing_error".to_string(),
                error_message: e.to_string(),
                component: "video_processor".to_string(),
                platform: std::env::consts::OS.to_string(),
                severity: "warning".to_string(),
                details: Some(serde_json::json!({
                    "job_id": job_id,
                    "parser": request.parser,
                    "encoder": request.encoder,
                })),
            })
            .ok();

            // Update job as failed
            db.update_job_metric(
                &job_id,
                0,
                0,
                "failed".to_string(),
                false,
                Some(&e.to_string()),
            )
            .ok();

            Err(ErrorResponse::new(
                "Processing failed",
                Some(&e.to_string()),
            ))
        }
    }
}

#[tauri::command]
pub fn get_dashboard_data(state: State<AppState>) -> Result<DashboardData, ErrorResponse> {
    let db = state.db.lock().unwrap();

    let errors = db
        .get_errors_24h()
        .map_err(|e| ErrorResponse::new("Failed to fetch errors", Some(&e.to_string())))?;
    let jobs = db
        .get_jobs_24h()
        .map_err(|e| ErrorResponse::new("Failed to fetch jobs", Some(&e.to_string())))?;

    let critical_errors = errors.iter().filter(|e| e.severity == "critical").count() as u32;
    let total_errors = errors.len() as u32;

    let successful_jobs = jobs.iter().filter(|j| j.success).count() as u32;
    let failed_jobs = jobs.iter().filter(|j| !j.success).count() as u32;
    let total_jobs = jobs.len() as u32;
    let total_records = jobs.iter().filter_map(|j| j.records_processed).sum::<u64>();

    // Count parsers and encoders
    let mut parsers = serde_json::json!({});
    let mut encoders = serde_json::json!({});

    for job in &jobs {
        *parsers[&job.parser_used].as_u64().unwrap_or(0) += 1;
        *encoders[&job.encoder_used].as_u64().unwrap_or(0) += 1;
    }

    Ok(DashboardData {
        total_errors,
        critical_errors,
        total_jobs,
        successful_jobs,
        failed_jobs,
        total_records_processed: total_records,
        parsers_used: parsers,
        encoders_used: encoders,
        benchmarks: serde_json::json!({}),
    })
}

#[tauri::command]
pub fn get_errors(
    limit: Option<i32>,
    severity: Option<String>,
    state: State<AppState>,
) -> Result<Vec<ErrorReport>, ErrorResponse> {
    let db = state.db.lock().unwrap();
    let errors = db
        .get_errors_24h()
        .map_err(|e| ErrorResponse::new("Failed to fetch errors", Some(&e.to_string())))?;

    let mut filtered: Vec<_> = errors
        .into_iter()
        .filter(|e| severity.is_none() || e.severity == severity.as_ref().unwrap().as_str())
        .collect();

    filtered.sort_by(|a, b| b.timestamp.cmp(&a.timestamp));
    filtered.truncate(limit.unwrap_or(10) as usize);

    Ok(filtered)
}

#[tauri::command]
pub fn get_job_stats(
    hours: Option<i32>,
    state: State<AppState>,
) -> Result<serde_json::Value, ErrorResponse> {
    let db = state.db.lock().unwrap();
    let jobs = db
        .get_jobs_24h()
        .map_err(|e| ErrorResponse::new("Failed to fetch jobs", Some(&e.to_string())))?;

    let completed = jobs.iter().filter(|j| j.success).count() as u32;
    let failed = jobs.iter().filter(|j| !j.success).count() as u32;
    let total_records: u64 = jobs.iter().filter_map(|j| j.records_processed).sum();
    let avg_duration: i32 = if !jobs.is_empty() {
        jobs.iter().filter_map(|j| j.duration_ms).sum::<i32>() / jobs.len() as i32
    } else {
        0
    };

    Ok(serde_json::json!({
        "completed": completed,
        "failed": failed,
        "total_records_processed": total_records,
        "average_duration_ms": avg_duration,
        "success_rate": if completed + failed > 0 {
            (completed as f32 / (completed + failed) as f32) * 100.0
        } else {
            0.0
        }
    }))
}

#[tauri::command]
pub fn export_telemetry(
    export_path: String,
    state: State<AppState>,
) -> Result<String, ErrorResponse> {
    let db = state.db.lock().unwrap();

    let errors = db
        .get_errors_24h()
        .map_err(|e| ErrorResponse::new("Failed to fetch errors", Some(&e.to_string())))?;
    let jobs = db
        .get_jobs_24h()
        .map_err(|e| ErrorResponse::new("Failed to fetch jobs", Some(&e.to_string())))?;

    let export_data = serde_json::json!({
        "exported_at": Utc::now().to_rfc3339(),
        "errors": errors,
        "jobs": jobs,
        "summary": {
            "total_errors": errors.len(),
            "total_jobs": jobs.len(),
            "successful_jobs": jobs.iter().filter(|j| j.success).count(),
            "failed_jobs": jobs.iter().filter(|j| !j.success).count(),
        }
    });

    std::fs::write(&export_path, export_data.to_string())
        .map_err(|e| ErrorResponse::new("Failed to write export file", Some(&e.to_string())))?;

    Ok(format!("Exported to {}", export_path))
}

#[tauri::command]
pub fn get_settings(state: State<AppState>) -> Result<serde_json::Value, ErrorResponse> {
    let settings = state.settings.lock().unwrap();
    Ok(settings.to_json())
}

#[tauri::command]
pub fn update_settings(
    settings: serde_json::Value,
    state: State<AppState>,
) -> Result<(), ErrorResponse> {
    let mut settings_mgr = state.settings.lock().unwrap();
    settings_mgr
        .update_from_json(settings)
        .map_err(|e| ErrorResponse::new("Failed to update settings", Some(&e.to_string())))
}
