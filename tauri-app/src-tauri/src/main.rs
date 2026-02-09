use tauri::Manager;
#[cfg(target_os = "macos")]
use tauri::TitleBarStyle;

mod sonarsniffer;

use sonarsniffer::{
    AppState, process_video, get_dashboard_data, get_errors, get_job_stats,
    export_telemetry, get_settings, update_settings,
    db::Database,
    settings::SettingsManager,
    telemetry::TelemetryManager,
    video_processor::VideoProcessor,
};
use std::sync::Mutex;

fn main() {
    tauri::Builder::default()
        .manage(AppState {
            db: Mutex::new(Database::new("sonarsniffer.db").expect("Failed to initialize database")),
            telemetry: Mutex::new(TelemetryManager::new(true)),
            settings: Mutex::new(SettingsManager::new()),
            processor: Mutex::new(VideoProcessor::new(true)),
        })
        .invoke_handler(tauri::generate_handler![
            process_video,
            get_dashboard_data,
            get_errors,
            get_job_stats,
            export_telemetry,
            get_settings,
            update_settings,
        ])
        .setup(|app| {
            #[cfg(target_os = "macos")]
            app.get_window("main").unwrap()
                .set_title_bar_style(TitleBarStyle::Overlay)
                .ok();

            Ok(())
        })
        .window_config(Default::default())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
