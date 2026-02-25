const { invoke } = window.__TAURI__.core;

let selectedFilePath = null;
let selectedFirmwarePath = null;
let selectedCorpusPath = null;

function setLabel(id, value, fallback) {
  const el = document.getElementById(id);
  el.textContent = value || fallback;
}

function renderResult(id, value) {
  const el = document.getElementById(id);
  el.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
}

// ── Rich pipeline result renderer ─────────────────────────────────────────────

function esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function depthRange(stats) {
  // stats = [min_ft, max_ft, avg_ft] from the Rust backend,
  // computed before pings are cleared so they survive the IPC response.
  if (!stats || stats.length < 3 || (stats[0] === 0 && stats[1] === 0)) return "—";
  return `${stats[0].toFixed(1)} ft – ${stats[1].toFixed(1)} ft (avg ${stats[2].toFixed(1)} ft)`;
}

function renderPipelineResult(result) {
  const el = document.getElementById("output-summary");

  const statusClass = result.status.startsWith("Pipe") ? "status-ok" : "status-err";
  const parse = result.parse || {};
  const outputs = result.outputs || null;
  const video = result.video || null;

  // Parse stats
  const channels = parse.channel_counts
    ? Object.keys(parse.channel_counts).join(", ")
    : "—";
  const depth = depthRange(result.depth_stats);

  let html = `<div class="pr-header ${statusClass}">${esc(result.status)}</div>`;

  // ── Parse section
  html += `<div class="pr-section">
    <div class="pr-section-title">Parse</div>
    <div class="stat-grid">
      <div class="stat"><span class="stat-lbl">Input</span><span class="stat-val mono">${esc(result.input_file)}</span></div>
      <div class="stat"><span class="stat-lbl">Records</span><span class="stat-val">${esc(parse.record_count ?? "—")}</span></div>
      <div class="stat"><span class="stat-lbl">Channels</span><span class="stat-val">${esc(channels)}</span></div>
      <div class="stat"><span class="stat-lbl">CRC mismatches</span><span class="stat-val">${esc(parse.crc_mismatch_count ?? "—")}</span></div>
      <div class="stat"><span class="stat-lbl">Dropped bytes</span><span class="stat-val">${esc(parse.dropped_bytes ?? "—")}</span></div>
      <div class="stat"><span class="stat-lbl">Depth range</span><span class="stat-val">${esc(depth)}</span></div>
    </div>
  </div>`;

  // ── Outputs section
  if (outputs) {
    html += `<div class="pr-section">
      <div class="pr-section-title">Output Files</div>
      <div class="artifact-dir">
        <span class="mono">${esc(outputs.output_dir)}</span>
        <button class="btn-sm" data-reveal="${esc(outputs.output_dir)}">Open Folder</button>
      </div>
      <div class="artifact-list">`;

    for (const art of outputs.artifacts || []) {
      const fname = art.path.split(/[\\/]/).pop();
      html += `<div class="artifact-row">
        <span class="artifact-kind">${esc(art.kind)}</span>
        <span class="artifact-path mono" title="${esc(art.path)}">${esc(fname)}</span>
        <span class="artifact-details">${esc(art.details)}</span>
        <button class="btn-sm" data-reveal="${esc(art.path)}">Open</button>
      </div>`;
    }

    html += `</div></div>`;
  } else if (parse.error_message) {
    html += `<div class="pr-section"><div class="pr-section-title">Output Files</div><span class="status-err">Skipped — parse error</span></div>`;
  }

  // ── Video section
  if (video !== null) {
    const vidOk = video.enabled && video.output_path;
    const vidClass = !video.enabled ? "status-warn" : vidOk ? "status-ok" : "status-warn";
    html += `<div class="pr-section">
      <div class="pr-section-title">Video Export</div>
      <div class="video-row">
        <span class="${vidClass}">${esc(video.status)}</span>`;
    if (video.output_path) {
      html += `<button class="btn-sm" data-reveal="${esc(video.output_path)}">Open</button>`;
    }
    html += `</div></div>`;
  }

  el.innerHTML = html;

  // Wire reveal buttons
  el.querySelectorAll("button[data-reveal]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const path = btn.getAttribute("data-reveal");
      try {
        await invoke("reveal_path", { path });
      } catch (err) {
        console.error("reveal_path failed:", err);
      }
    });
  });
}

// ── Event wiring ──────────────────────────────────────────────────────────────

window.addEventListener("DOMContentLoaded", () => {
  const fileBtn = document.getElementById("file-btn");
  const firmwareBtn = document.getElementById("firmware-btn");
  const corpusBtn = document.getElementById("corpus-btn");
  const outputDirBtn = document.getElementById("output-dir-btn");

  const parserForm = document.getElementById("rsd-form");
  const firmwareForm = document.getElementById("firmware-form");
  const corpusForm = document.getElementById("corpus-form");

  fileBtn.addEventListener("click", async () => {
    const file = await invoke("pick_input_file");
    if (file) {
      selectedFilePath = file;
      setLabel("file-label", file, "No file selected");
    }
  });

  firmwareBtn.addEventListener("click", async () => {
    const file = await invoke("pick_any_file");
    if (file) {
      selectedFirmwarePath = file;
      setLabel("firmware-label", file, "No file selected");
    }
  });

  corpusBtn.addEventListener("click", async () => {
    const folder = await invoke("pick_folder");
    if (folder) {
      selectedCorpusPath = folder;
      setLabel("corpus-label", folder, "No folder selected");
    }
  });

  outputDirBtn.addEventListener("click", async () => {
    const folder = await invoke("pick_folder");
    if (folder) {
      document.getElementById("output-dir").value = folder;
    }
  });

  parserForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const summaryEl = document.getElementById("output-summary");
    summaryEl.innerHTML = '<span class="status-running">Running parser pipeline\u2026</span>';

    if (!selectedFilePath) {
      setLabel("file-label", null, "No file selected");
      summaryEl.innerHTML = '<span class="status-err">Please select an .RSD file.</span>';
      return;
    }

    const outputDir = document.getElementById("output-dir").value.trim();
    const options = {
      video: document.getElementById("video-opt").checked,
      kml: document.getElementById("kml-opt").checked,
      kmz: document.getElementById("kmz-opt").checked,
      mbtiles: document.getElementById("mbtiles-opt").checked,
      mosaic: document.getElementById("mosaic-opt").checked,
      waterfall: document.getElementById("waterfall-opt").checked,
      arcgis: document.getElementById("arcgis-opt").checked,
      webViewer: document.getElementById("viewer-opt").checked,
      colormap: document.getElementById("colormap-opt").value,
      outputDir: outputDir.length ? outputDir : null,
    };

    try {
      const result = await invoke("run_sonar_pipeline", {
        fileName: selectedFilePath,
        options,
      });
      renderPipelineResult(result);
    } catch (err) {
      summaryEl.innerHTML = `<span class="status-err">Error: ${esc(String(err))}</span>`;
    }
  });

  firmwareForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    renderResult("firmware-summary", "Running firmware analysis\u2026");

    if (!selectedFirmwarePath) {
      setLabel("firmware-label", null, "No file selected");
      renderResult("firmware-summary", "Please select a firmware file.");
      return;
    }

    try {
      const result = await invoke("analyze_firmware", {
        fileName: selectedFirmwarePath,
      });
      renderResult("firmware-summary", result);
    } catch (err) {
      renderResult("firmware-summary", `Error: ${err}`);
    }
  });

  corpusForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    renderResult("corpus-summary", "Scanning corpus directory\u2026");

    if (!selectedCorpusPath) {
      setLabel("corpus-label", null, "No folder selected");
      renderResult("corpus-summary", "Please select a corpus folder.");
      return;
    }

    try {
      const result = await invoke("scan_corpus_directory", {
        rootDir: selectedCorpusPath,
      });
      renderResult("corpus-summary", result);
    } catch (err) {
      renderResult("corpus-summary", `Error: ${err}`);
    }
  });
});

