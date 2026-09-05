// SonarSniffer browser pipeline — main app entry.
import init, {
  version,
  greet,
  looks_like_rsd,
  parse_rsd_bytes,
  max_pings_in_json,
  ping_samples,
} from "./pkg/sonarsniffer_lib.js";

const state = { wasm: false, handle: null, selectedChannel: null };
const $ = (id) => document.getElementById(id);

function setStep(name, mode) {
  const li = document.querySelector(`.pipeline li[data-step="${name}"]`);
  if (!li) return;
  li.classList.remove("active", "done");
  if (mode) li.classList.add(mode);
}

function resetSteps(...names) {
  for (const n of names) setStep(n, null);
  document.querySelectorAll(".pipeline li.done").forEach((el) => el.classList.remove("done"));
}

function setProgress(pct, text) {
  $("progressBar").value = pct;
  if (text) $("progressText").textContent = text;
}

function showError(msg) {
  $("errorCard").hidden = false;
  $("errorText").textContent = msg;
  const pill = $("wasmStatus");
  pill.className = "pill error";
  pill.textContent = "error";
}

function fmtBytes(n) {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`;
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}

const tick = () => new Promise((r) => setTimeout(r, 0));

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));
}

async function boot() {
  setStep("load", "active");
  setProgress(5, "Loading WASM module…");
  try {
    await init();
  } catch (e) {
    showError("Failed to load WASM module: " + e);
    return;
  }
  state.wasm = true;
  setStep("load", "done");
  setProgress(15, "Ready.  Drop a .RSD file to begin.");

  let v = "?";
  try { v = version(); } catch (_) {}
  $("versionPill").textContent = "v" + v;
  $("versionFooter").textContent = v;
  $("wasmStatus").className = "pill ok";
  $("wasmStatus").textContent = "WASM ready";

  try { console.log(greet()); } catch (_) {}

  wireDropzone();
  wireFileInput();
}

function wireDropzone() {
  const dz = $("dropZone");
  const fi = $("fileInput");
  const pick = $("pickFileBtn");
  pick.addEventListener("click", () => fi.click());
  dz.addEventListener("click", (ev) => {
    if (ev.target.closest("button")) return;
    fi.click();
  });
  dz.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); fi.click(); }
  });
  ["dragenter", "dragover"].forEach((evt) => {
    dz.addEventListener(evt, (e) => { e.preventDefault(); dz.classList.add("drag"); });
  });
  ["dragleave", "drop"].forEach((evt) => {
    dz.addEventListener(evt, (e) => { e.preventDefault(); dz.classList.remove("drag"); });
  });
  dz.addEventListener("drop", (ev) => {
    const file = ev.dataTransfer?.files?.[0];
    if (file) handleFile(file);
  });
}

function wireFileInput() {
  $("fileInput").addEventListener("change", (ev) => {
    const file = ev.target.files?.[0];
    if (file) handleFile(file);
  });
}

async function handleFile(file) {
  $("errorCard").hidden = true;
  $("fileInfo").hidden = false;
  $("fileName").textContent = file.name;
  $("fileSize").textContent = fmtBytes(file.size);

  const bytes = new Uint8Array(await file.arrayBuffer());

  resetSteps("sniff", "parse", "discover", "render");
  setStep("sniff", "active");
  setProgress(20, `Read ${fmtBytes(file.size)} from disk. Sniffing…`);
  await tick();
  if (!looks_like_rsd(bytes)) {
    showError(
      `Not a Garmin RSD file.  First 4 bytes: 0x${[...bytes.slice(0, 4)]
        .map((b) => b.toString(16).padStart(2, "0"))
        .join("")}`
    );
    return;
  }
  setStep("sniff", "done");
  setProgress(30, "Magic OK.  Parsing records…");

  setStep("parse", "active");
  await tick();
  let out;
  const t0 = performance.now();
  try {
    out = parse_rsd_bytes(bytes);
  } catch (e) {
    showError("parse_rsd_bytes failed: " + e);
    return;
  }
  const parseMs = performance.now() - t0;
  setStep("parse", "done");
  setStep("discover", "active");
  await tick();
  setStep("discover", "done");
  setStep("render", "active");
  setProgress(80, `Parse + discover in ${parseMs.toFixed(0)} ms.  Rendering…`);

  renderResult(out, file.size, parseMs);
  setStep("render", "done");
  setProgress(100, "Done.");
}

function renderResult(out, fileBytes, parseMs) {
  $("resultCard").hidden = false;
  $("kpiRecords").textContent = out.parse.record_count.toLocaleString();
  $("kpiChannels").textContent = (out.parse.channels || []).length.toLocaleString();
  $("kpiDiscoveryPings").textContent = out.discovery_ping_count.toLocaleString();
  const medSamples = (out.channel_summary || []).length > 0
    ? Math.round(
        out.channel_summary.reduce((s, c) => s + c.median_sample_count, 0) /
          out.channel_summary.length
      )
    : 0;
  $("kpiSampleCount").textContent = medSamples.toLocaleString();
  $("kpiSidescanPairs").textContent = (out.discovery.sidescan_pairs || []).length;

  renderChannels(out);
  renderDiscoveryLog(out);
  $("waterfallCard").hidden = false;
  $("waterfall").textContent = "Pick a channel above to preview its first pings.";
  state.handle = out;
}

function renderChannels(out) {
  const grid = $("channelGrid");
  grid.innerHTML = "";
  const list = out.channel_summary || [];
  $("channelsCard").hidden = false;
  $("channelsNote").textContent = list.length === 0
    ? "No channels were discovered in this file."
    : `${list.length} channel(s) discovered.  Click any to draw its waterfall preview.`;

  for (const c of list) {
    const btn = document.createElement("button");
    btn.className = "channel";
    btn.type = "button";
    btn.dataset.channel = c.channel;
    btn.innerHTML = `
      <div class="ch-id">ch${c.channel}</div>
      <div class="ch-role">${escapeHtml(c.spatial_role)}${c.was_flipped ? ' (flipped)' : ''}</div>
      <div class="ch-meta">
        ${c.ping_count.toLocaleString()} pings ·
        ${c.gps_ping_count.toLocaleString()} with GPS ·
        ${c.median_sample_count.toLocaleString()} samples
      </div>
      <div class="ch-meta">
        archetype: ${escapeHtml(c.archetype)} · tier: ${escapeHtml(c.frequency_tier)} ·
        conf ${(c.archetype_confidence * 100).toFixed(0)}%
      </div>
      <div class="ch-reason">${escapeHtml(c.classification_reason)}</div>
    `;
    btn.addEventListener("click", () => selectChannel(c.channel, btn));
    grid.appendChild(btn);
  }
}

function renderDiscoveryLog(out) {
  $("logCard").hidden = false;
  const log = (out.discovery.discovery_log || []).join("\n");
  $("discoveryLog").textContent = log || "(no discovery log)";
}

async function selectChannel(channel, btn) {
  document.querySelectorAll(".channel.selected").forEach((el) => el.classList.remove("selected"));
  btn.classList.add("selected");
  state.selectedChannel = channel;

  if (!state.handle) return;
  const wf = $("waterfall");
  wf.textContent = `Drawing ch${channel}…`;
  await tick();

  const summary = (state.handle.channel_summary || []).find((c) => c.channel === channel);
  if (!summary) { wf.textContent = "(no profile)"; return; }
  const pings = (state.handle.pings || []).filter((p) => p.channel === channel);
  if (pings.length === 0) { wf.textContent = "(no pings on this channel in preview)"; return; }
  const firstN = Math.min(64, pings.length);

  wf.innerHTML = "";
  const canvas = document.createElement("canvas");
  canvas.width = 800;
  canvas.height = 220;
  wf.appendChild(canvas);
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  let chIndex = 0;
  const sampleCount = summary.median_sample_count || 0;
  const stride = 800 / Math.max(1, firstN);
  for (let i = 0; i < pings.length && chIndex < firstN; i++) {
    let samples = null;
    try {
      samples = ping_samples(state.handle, channel, chIndex);
    } catch (e) {
      samples = null;
    }
    chIndex += 1;
    if (!samples || !Array.isArray(samples) || samples.length === 0) continue;
    const max = Math.max(...samples) || 1;
    const x = Math.floor((chIndex - 1) * stride);
    const colW = Math.max(1, Math.floor(stride));
    for (let s = 0; s < samples.length; s++) {
      const v = samples[s] / max;
      const y = Math.floor((1 - v) * canvas.height);
      const intensity = Math.floor(v * 255);
      ctx.fillStyle = `rgb(${intensity * 0.4}, ${intensity}, ${255 - intensity * 0.3})`;
      ctx.fillRect(x, y, colW, 1);
    }
  }
  wf.appendChild(makeMetaLine(`ch${channel} · ${firstN}/${pings.length} pings · ${sampleCount} samples/ping`));
}

function makeMetaLine(text) {
  const div = document.createElement("div");
  div.className = "small muted";
  div.style.textAlign = "center";
  div.style.padding = "0.4rem 0 0";
  div.textContent = text;
  return div;
}

window.addEventListener("error", (ev) => {
  showError("Uncaught: " + (ev.error?.stack || ev.message));
});

boot();
