const invoke = window.__TAURI__?.core?.invoke;
const openUrl = window.__TAURI__?.plugin?.opener?.openUrl;

const state = {
  license: null,
  preflight: null,
};

function setText(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function setConsole(id, value) {
  const node = document.getElementById(id);
  if (node) node.textContent = value;
}

function prettyJson(value) {
  return JSON.stringify(value, null, 2);
}

function renderDepsList(containerId, report) {
  const ul = document.getElementById(containerId);
  if (!ul) return;
  ul.innerHTML = "";
  for (const item of report.items) {
    const li = document.createElement("li");
    li.className = item.satisfied ? "dep-ok" : "dep-missing";
    const status = item.satisfied ? "✔" : "✘";
    li.innerHTML = `<strong>${status} ${item.name}</strong><br><span class="muted">${item.message}</span>`;
    const actions = document.createElement("div");
    actions.className = "dep-actions";
    if (!item.satisfied && item.download_url) {
      const dl = document.createElement("button");
      dl.type = "button";
      dl.textContent = "Download page";
      dl.addEventListener("click", () => openDependency(item.id));
      actions.appendChild(dl);
    }
    if (!item.satisfied && item.can_auto_install) {
      const inst = document.createElement("button");
      inst.type = "button";
      inst.className = "primary";
      inst.textContent = "Auto-install";
      inst.addEventListener("click", () => installOne(item.id));
      actions.appendChild(inst);
    }
    if (item.install_hint && !item.satisfied) {
      const hint = document.createElement("code");
      hint.className = "install-hint";
      hint.textContent = item.install_hint;
      actions.appendChild(hint);
    }
    li.appendChild(actions);
    ul.appendChild(li);
  }
}

function applyPreflightUI(report) {
  state.preflight = report;
  const ready = report.ready;
  setText("dependencySummary", report.summary);
  setText("depsGateSummary", report.summary);
  setText("depsInlineMessage", ready ? "" : "Pipeline is locked until required items are installed.");
  setText("depsGateMessage", "");

  renderDepsList("depsList", report);
  renderDepsList("depsListInline", report);

  const gate = document.getElementById("depsGate");
  const runBtn = document.getElementById("runPipelineBtn");
  if (gate) gate.classList.toggle("hidden", ready);
  if (runBtn) runBtn.disabled = !ready;
}

async function refreshDependencies() {
  try {
    const report = await invoke("check_dependencies");
    applyPreflightUI(report);
  } catch (error) {
    setText("dependencySummary", `Dependency check failed: ${error}`);
  }
}

async function installAll() {
  setText("depsInlineMessage", "Installing… (winget may prompt for Administrator)");
  setText("depsGateMessage", "Installing…");
  try {
    const msg = await invoke("install_all_dependencies");
    setText("depsInlineMessage", msg);
    setText("depsGateMessage", msg);
    await refreshDependencies();
  } catch (error) {
    const text = String(error);
    setText("depsInlineMessage", text);
    setText("depsGateMessage", text);
    await refreshDependencies();
  }
}

async function installOne(id) {
  setText("depsInlineMessage", `Installing ${id}…`);
  try {
    const msg = await invoke("install_dependency", { id });
    setText("depsInlineMessage", msg);
    await refreshDependencies();
  } catch (error) {
    setText("depsInlineMessage", String(error));
    await refreshDependencies();
  }
}

async function openDependency(id) {
  try {
    if (openUrl) {
      const report = state.preflight;
      const item = report?.items?.find((i) => i.id === id);
      if (item?.download_url) await openUrl(item.download_url);
      return;
    }
    const msg = await invoke("open_dependency_url", { id });
    setText("depsInlineMessage", msg);
  } catch (error) {
    setText("depsInlineMessage", String(error));
  }
}

async function refreshLicense() {
  try {
    const status = await invoke("check_license");
    state.license = status;
    const buildFlavor = status.private_build ? "Private Build" : "Public Build";
    setText("buildFlavorBadge", buildFlavor);
    let summary = "License status unavailable.";
    if (status.state === "unlocked") {
      summary = status.private_build
        ? "Private build: license prompts are disabled."
        : "Full license active.";
    } else if (status.state === "trial") {
      const installed = status.first_installed ? ` (installed ${status.first_installed})` : "";
      summary = `30-day trial: ${status.days_remaining} day(s) remaining${installed}.`;
    } else {
      summary = "Trial expired. Enter your 20-digit license code to unlock SonarSniffer.";
    }
    setText("licenseSummary", summary);
    setText("licenseContact", `License support: ${status.contact_email}`);
    setText(
      "licenseMessage",
      status.private_build
        ? "This installer is pre-unlocked for internal use."
        : status.state === "trial"
          ? "Trial started on first launch. Video export uses built-in AV1 (rav1e)."
          : ""
    );
    const keyInput = document.getElementById("licenseKey");
    const activateButton = document.getElementById("activateLicenseBtn");
    const unlocked = status.private_build || status.state === "unlocked";
    if (keyInput) {
      keyInput.disabled = unlocked;
      if (unlocked) keyInput.value = "";
    }
    if (activateButton) activateButton.disabled = unlocked;
  } catch (error) {
    setText("licenseSummary", `License check failed: ${error}`);
  }
}

async function activateLicense() {
  const keyInput = document.getElementById("licenseKey");
  const key = keyInput?.value?.trim();
  if (!key) {
    setText("licenseMessage", "Enter your 20-digit license code first.");
    return;
  }
  const digits = key.replace(/\D/g, "");
  if (digits.length !== 20) {
    setText("licenseMessage", "License code must be exactly 20 digits.");
    return;
  }
  try {
    await invoke("activate_license", { key });
    if (keyInput) keyInput.value = "";
    setText("licenseMessage", "License activated. Thank you.");
    await refreshLicense();
  } catch (error) {
    setText("licenseMessage", String(error));
  }
}

async function browseInput(targetId) {
  try {
    const result = await invoke("pick_input_file");
    if (result) document.getElementById(targetId).value = result;
  } catch (error) {
    setConsole("pipelineOutput", `Browse failed: ${error}`);
  }
}

async function browseFolder() {
  try {
    const result = await invoke("pick_folder");
    if (result) document.getElementById("outputFolder").value = result;
  } catch (error) {
    setConsole("pipelineOutput", `Folder browse failed: ${error}`);
  }
}

async function runPipeline() {
  if (state.license?.state === "expired") {
    setConsole("pipelineOutput", `Trial expired. Enter a 20-digit license code or contact ${state.license.contact_email}.`);
    return;
  }
  if (!state.preflight?.ready) {
    setConsole("pipelineOutput", "Install required dependencies first (WebView2 on Windows).");
    return;
  }
  const fileName = document.getElementById("pipelineInput")?.value?.trim();
  if (!fileName) {
    setConsole("pipelineOutput", "Select an input file first.");
    return;
  }
  const outDir = document.getElementById("outputFolder")?.value?.trim();
  const selectedMap = document.querySelector(".swatch.selected")?.dataset?.map || "amber";
  const options = {
    video: Boolean(document.getElementById("enableVideo")?.checked),
    mosaic: Boolean(document.getElementById("enableMosaic")?.checked),
    curveletDenoise: Boolean(document.getElementById("enableCurvelet")?.checked),
    soundtiles: Boolean(document.getElementById("enableSoundtiles")?.checked),
    colormap: selectedMap,
    waterfall: true,
    kml: true,
    kmz: true,
    mbtiles: true,
    arcgis: true,
    webViewer: true,
  };
  if (outDir) options.output_dir = outDir;

  setConsole("pipelineOutput", "Running SonarSniffer pipeline...");
  try {
    const result = await invoke("run_sonar_pipeline", { fileName, options });
    setConsole("pipelineOutput", prettyJson(result));
  } catch (error) {
    setConsole("pipelineOutput", `Pipeline failed:\n${error}`);
  }
}

async function runSoundtiles() {
  const input = document.getElementById("soundtilesInput")?.value?.trim();
  if (!input) {
    setConsole("soundtilesOutput", "Select an input file first.");
    return;
  }
  const channel = document.getElementById("soundtilesChannel")?.value?.trim() || "auto";
  const tiles = Number(document.getElementById("soundtilesTiles")?.value || 20);
  const verbose = Boolean(document.getElementById("soundtilesVerbose")?.checked);
  setConsole("soundtilesOutput", "Running SoundTiles...");
  try {
    const result = await invoke("run_soundtiles", { input, channel, tiles, verbose });
    const combined = [
      `Executable: ${result.executable}`,
      `Exit code: ${result.exit_code}`,
      "",
      result.stdout || "<no stdout>",
      result.stderr ? `\n[stderr]\n${result.stderr}` : "",
    ].join("\n");
    setConsole("soundtilesOutput", combined);
  } catch (error) {
    setConsole("soundtilesOutput", `SoundTiles failed:\n${error}`);
  }
}

window.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("activateLicenseBtn")?.addEventListener("click", activateLicense);
  document.getElementById("refreshDepsBtn")?.addEventListener("click", refreshDependencies);
  document.getElementById("refreshDepsBtn2")?.addEventListener("click", refreshDependencies);
  document.getElementById("installAllDepsBtn")?.addEventListener("click", installAll);
  document.getElementById("installAllDepsBtnInline")?.addEventListener("click", installAll);
  document.getElementById("browsePipelineBtn")?.addEventListener("click", () => browseInput("pipelineInput"));
  document.getElementById("browseSoundtilesBtn")?.addEventListener("click", () => browseInput("soundtilesInput"));
  document.getElementById("browseFolderBtn")?.addEventListener("click", browseFolder);
  document.getElementById("runPipelineBtn")?.addEventListener("click", runPipeline);
  document.getElementById("runSoundtilesBtn")?.addEventListener("click", runSoundtiles);

  // Colormap swatch selection
  document.getElementById("colormapSwatches")?.addEventListener("click", (e) => {
    const btn = e.target.closest(".swatch");
    if (!btn) return;
    document.querySelectorAll(".swatch").forEach((s) => s.classList.remove("selected"));
    btn.classList.add("selected");
  });

  await Promise.all([refreshLicense(), refreshDependencies()]);
});
