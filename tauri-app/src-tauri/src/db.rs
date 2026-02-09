use anyhow::Result;
use chrono::{DateTime, Duration, Utc};
use rusqlite::{params, Connection};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ErrorReport {
    pub timestamp: String,
    pub error_type: String,
    pub error_message: String,
    pub component: String,
    pub platform: String,
    pub severity: String,
    pub details: Option<serde_json::Value>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct JobMetric {
    pub job_id: String,
    pub timestamp: String,
    pub status: String,
    pub records_processed: Option<u64>,
    pub duration_ms: Option<i32>,
    pub parser_used: String,
    pub encoder_used: String,
    pub video_resolution: Option<String>,
    pub output_file_size: Option<u64>,
    pub success: bool,
    pub error_message: Option<String>,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct BenchmarkRecord {
    pub timestamp: String,
    pub parser: String,
    pub throughput: f32,
    pub latency_ms: f32,
    pub samples: i32,
}

pub struct Database {
    conn: Connection,
}

impl Database {
    pub fn new(path: &str) -> Result<Self> {
        let conn = Connection::open(path)?;
        let db = Database { conn };
        db.init_schema()?;
        Ok(db)
    }

    fn init_schema(&self) -> Result<()> {
        self.conn.execute_batch(
            "
            CREATE TABLE IF NOT EXISTS error_reports (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                error_type TEXT NOT NULL,
                error_message TEXT NOT NULL,
                component TEXT NOT NULL,
                platform TEXT,
                severity TEXT,
                details TEXT
            );

            CREATE TABLE IF NOT EXISTS job_metrics (
                id INTEGER PRIMARY KEY,
                job_id TEXT NOT NULL UNIQUE,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                records_processed INTEGER,
                duration_ms INTEGER,
                parser_used TEXT NOT NULL,
                encoder_used TEXT NOT NULL,
                video_resolution TEXT,
                output_file_size INTEGER,
                success BOOLEAN NOT NULL,
                error_message TEXT
            );

            CREATE TABLE IF NOT EXISTS benchmarks (
                id INTEGER PRIMARY KEY,
                timestamp TEXT NOT NULL,
                parser TEXT NOT NULL,
                throughput REAL NOT NULL,
                latency_ms REAL NOT NULL,
                samples INTEGER NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_errors_timestamp ON error_reports(timestamp);
            CREATE INDEX IF NOT EXISTS idx_jobs_timestamp ON job_metrics(timestamp);
            CREATE INDEX IF NOT EXISTS idx_benchmarks_timestamp ON benchmarks(timestamp);
            ",
        )?;
        Ok(())
    }

    pub fn insert_error_report(&mut self, error: ErrorReport) -> Result<()> {
        self.conn.execute(
            "INSERT INTO error_reports (timestamp, error_type, error_message, component, platform, severity, details)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                error.timestamp,
                error.error_type,
                error.error_message,
                error.component,
                error.platform,
                error.severity,
                error.details.map(|d| d.to_string()),
            ],
        )?;
        Ok(())
    }

    pub fn insert_job_metric(&mut self, job: JobMetric) -> Result<()> {
        self.conn.execute(
            "INSERT INTO job_metrics (job_id, timestamp, status, records_processed, duration_ms, parser_used, encoder_used, video_resolution, output_file_size, success, error_message)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
            params![
                job.job_id,
                job.timestamp,
                job.status,
                job.records_processed,
                job.duration_ms,
                job.parser_used,
                job.encoder_used,
                job.video_resolution,
                job.output_file_size,
                job.success,
                job.error_message,
            ],
        )?;
        Ok(())
    }

    pub fn update_job_metric(
        &mut self,
        job_id: &str,
        records: i32,
        duration: i32,
        status: String,
        success: bool,
        error_msg: Option<&str>,
    ) -> Result<()> {
        self.conn.execute(
            "UPDATE job_metrics SET records_processed = ?1, duration_ms = ?2, status = ?3, success = ?4, error_message = ?5
             WHERE job_id = ?6",
            params![records, duration, status, success, error_msg, job_id],
        )?;
        Ok(())
    }

    pub fn get_errors_24h(&self) -> Result<Vec<ErrorReport>> {
        let cutoff = Utc::now() - Duration::hours(24);
        let mut stmt = self.conn.prepare(
            "SELECT timestamp, error_type, error_message, component, platform, severity, details
             FROM error_reports WHERE timestamp > ?1 ORDER BY timestamp DESC",
        )?;

        let errors = stmt.query_map(params![cutoff.to_rfc3339()], |row| {
            Ok(ErrorReport {
                timestamp: row.get(0)?,
                error_type: row.get(1)?,
                error_message: row.get(2)?,
                component: row.get(3)?,
                platform: row.get(4)?,
                severity: row.get(5)?,
                details: row
                    .get::<_, Option<String>>(6)?
                    .and_then(|s| serde_json::from_str(&s).ok()),
            })
        })?;

        let mut result = Vec::new();
        for error in errors {
            result.push(error?);
        }
        Ok(result)
    }

    pub fn get_jobs_24h(&self) -> Result<Vec<JobMetric>> {
        let cutoff = Utc::now() - Duration::hours(24);
        let mut stmt = self.conn.prepare(
            "SELECT job_id, timestamp, status, records_processed, duration_ms, parser_used, encoder_used, video_resolution, output_file_size, success, error_message
             FROM job_metrics WHERE timestamp > ?1 ORDER BY timestamp DESC"
        )?;

        let jobs = stmt.query_map(params![cutoff.to_rfc3339()], |row| {
            Ok(JobMetric {
                job_id: row.get(0)?,
                timestamp: row.get(1)?,
                status: row.get(2)?,
                records_processed: row.get(3)?,
                duration_ms: row.get(4)?,
                parser_used: row.get(5)?,
                encoder_used: row.get(6)?,
                video_resolution: row.get(7)?,
                output_file_size: row.get(8)?,
                success: row.get(9)?,
                error_message: row.get(10)?,
            })
        })?;

        let mut result = Vec::new();
        for job in jobs {
            result.push(job?);
        }
        Ok(result)
    }

    pub fn insert_benchmark(&mut self, benchmark: BenchmarkRecord) -> Result<()> {
        self.conn.execute(
            "INSERT INTO benchmarks (timestamp, parser, throughput, latency_ms, samples)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            params![
                benchmark.timestamp,
                benchmark.parser,
                benchmark.throughput,
                benchmark.latency_ms,
                benchmark.samples,
            ],
        )?;
        Ok(())
    }

    pub fn get_benchmarks_24h(&self) -> Result<Vec<BenchmarkRecord>> {
        let cutoff = Utc::now() - Duration::hours(24);
        let mut stmt = self.conn.prepare(
            "SELECT timestamp, parser, throughput, latency_ms, samples
             FROM benchmarks WHERE timestamp > ?1 ORDER BY timestamp DESC",
        )?;

        let benchmarks = stmt.query_map(params![cutoff.to_rfc3339()], |row| {
            Ok(BenchmarkRecord {
                timestamp: row.get(0)?,
                parser: row.get(1)?,
                throughput: row.get(2)?,
                latency_ms: row.get(3)?,
                samples: row.get(4)?,
            })
        })?;

        let mut result = Vec::new();
        for benchmark in benchmarks {
            result.push(benchmark?);
        }
        Ok(result)
    }
}
