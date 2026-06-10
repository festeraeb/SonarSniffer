//! Multi-file mosaic merge (experimental).
//!
//! DEBUG tomorrow: needs shared colormap norm across runs + GPS overlap handling.

use crate::garmin_rsd_parser::ParseResult;
use anyhow::{bail, Context, Result};
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, serde::Serialize)]
pub struct MultiMosaicPlan {
    pub input_files: Vec<String>,
    pub output_dir: String,
    pub shared_colormap: String,
    pub notes: Vec<String>,
}

/// Plan a multi-run merge. Full pixel merge is not yet implemented — returns a plan JSON artifact.
pub fn plan_multi_mosaic(
    inputs: &[PathBuf],
    output_dir: &Path,
    colormap: &str,
) -> Result<MultiMosaicPlan> {
    if inputs.len() < 2 {
        bail!("multi_mosaic requires at least two input files");
    }
    for p in inputs {
        if !p.exists() {
            bail!("missing input: {}", p.display());
        }
    }
    std::fs::create_dir_all(output_dir)
        .with_context(|| format!("create {}", output_dir.display()))?;

    let plan = MultiMosaicPlan {
        input_files: inputs
            .iter()
            .map(|p| p.display().to_string())
            .collect(),
        output_dir: output_dir.display().to_string(),
        shared_colormap: colormap.to_string(),
        notes: vec![
            "v0.8.8 stub: per-file mosaics run separately; unified grid merge pending".into(),
            "Use identical colormap + removeWaterColumn for visual consistency".into(),
            "Overlap trim by timestamp will be added in next iteration".into(),
        ],
    };

    let plan_path = output_dir.join("multi_mosaic_plan.json");
    std::fs::write(&plan_path, serde_json::to_vec_pretty(&plan)?)?;
    Ok(plan)
}

/// Parse multiple files (caller supplies parsed results). Stitch not implemented yet.
pub fn merge_parsed_runs(_runs: &[ParseResult]) -> Result<()> {
    bail!("merge_parsed_runs not implemented — see multi_mosaic_plan.json notes");
}
