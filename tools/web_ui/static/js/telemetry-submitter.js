/**
 * telemetry-submitter.js
 * Frictionless GitHub Pull Request submission for Assetto Corsa AI Telemetry profiles.
 * Integrates Google OAuth identity validation, client-side JSON parsing/metrics,
 * and automated Pull Request creation via serverless gateway.
 */

import { api, isStaticHost } from "./api.js";
import { dom } from "./dom.js";
import { showToast, escapeHtml } from "./ui-utils.js";

let googleUser = null;
let parsedTelemetry = null;

/**
 * Initialize telemetry submitter modal and event handlers.
 */
export function initTelemetrySubmitter() {
  const btnOpen = dom.btnOpenSubmitPrModal || document.getElementById("btn-open-submit-pr-modal");
  if (btnOpen) {
    if (!isStaticHost()) {
      btnOpen.style.display = "none";
    }
  }
  const modal = document.getElementById("modal-submit-pr");
  const btnClose = document.getElementById("modal-submit-pr-close");
  const btnCancel = document.getElementById("btn-submit-pr-cancel");
  const btnSubmit = document.getElementById("btn-submit-telemetry-pr");

  const dropzone = document.getElementById("telemetry-dropzone");
  const fileInput = document.getElementById("telemetry-file-input");

  const btnManualAuth = document.getElementById("btn-manual-contributor-id");
  const btnSignout = document.getElementById("btn-signout-google");

  if (btnOpen && modal) {
    btnOpen.addEventListener("click", () => {
      openSubmitModal();
    });
  }

  if (btnClose && modal) {
    btnClose.addEventListener("click", () => {
      closeSubmitModal();
    });
  }

  if (btnCancel && modal) {
    btnCancel.addEventListener("click", () => {
      closeSubmitModal();
    });
  }

  // File Dropzone handlers
  if (dropzone && fileInput) {
    dropzone.addEventListener("click", () => fileInput.click());

    dropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      dropzone.style.borderColor = "#38bdf8";
      dropzone.style.background = "rgba(56, 189, 248, 0.1)";
    });

    dropzone.addEventListener("dragleave", () => {
      dropzone.style.borderColor = "rgba(56, 189, 248, 0.35)";
      dropzone.style.background = "rgba(15, 23, 42, 0.4)";
    });

    dropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      dropzone.style.borderColor = "rgba(56, 189, 248, 0.35)";
      dropzone.style.background = "rgba(15, 23, 42, 0.4)";
      if (e.dataTransfer?.files?.length) {
        void handleFileSelected(e.dataTransfer.files[0]);
      }
    });

    fileInput.addEventListener("change", () => {
      if (fileInput.files?.length) {
        void handleFileSelected(fileInput.files[0]);
      }
    });
  }

  // Contributor Sign In
  if (btnManualAuth) {
    btnManualAuth.addEventListener("click", () => {
      promptContributorAuth();
    });
  }

  if (btnSignout) {
    btnSignout.addEventListener("click", () => {
      clearGoogleAuth();
    });
  }

  // Submit PR button
  if (btnSubmit) {
    btnSubmit.addEventListener("click", () => {
      void executeSubmitPR();
    });
  }

  // Check stored auth
  restoreSavedAuth();
}

/**
 * Open the submission modal and reset cards.
 */
function openSubmitModal() {
  const modal = document.getElementById("modal-submit-pr");
  if (!modal) return;

  modal.style.display = "flex";
  const successCard = document.getElementById("pr-success-card");
  const statusDiv = document.getElementById("pr-submission-status");
  if (successCard) successCard.style.display = "none";
  if (statusDiv) statusDiv.style.display = "none";

  updateSubmitButtonState();
}

/**
 * Close modal.
 */
function closeSubmitModal() {
  const modal = document.getElementById("modal-submit-pr");
  if (modal) modal.style.display = "none";
}

/**
 * Prompt contributor for identity when GIS library is not loaded.
 */
function promptContributorAuth() {
  const defaultName = localStorage.getItem("gt_contributor_name") || "";
  const name = prompt("Enter your Name or Nickname for the Pull Request credit:", defaultName);
  if (!name || !name.trim()) return;

  const defaultEmail = localStorage.getItem("gt_contributor_email") || "";
  const email = prompt("Enter your Email (for GitHub contribution credit):", defaultEmail);
  if (!email || !email.trim()) return;

  setAuthenticatedUser({
    name: name.trim(),
    email: email.trim(),
    token: "demo_token",
  });
}

/**
 * Restores previously stored credentials if any.
 */
function restoreSavedAuth() {
  const savedName = localStorage.getItem("gt_contributor_name");
  const savedEmail = localStorage.getItem("gt_contributor_email");
  if (savedName && savedEmail) {
    setAuthenticatedUser({
      name: savedName,
      email: savedEmail,
      token: "demo_token",
    });
  }
}

/**
 * Sets authenticated contributor state and updates UI.
 */
function setAuthenticatedUser(user) {
  googleUser = user;
  if (user) {
    localStorage.setItem("gt_contributor_name", user.name);
    localStorage.setItem("gt_contributor_email", user.email);
  }

  const badge = document.getElementById("user-profile-badge");
  const nameSpan = document.getElementById("user-display-name");
  const authStatus = document.getElementById("google-auth-status");
  const btnManual = document.getElementById("btn-manual-contributor-id");

  if (user) {
    if (badge) badge.style.display = "inline-flex";
    if (nameSpan) nameSpan.textContent = `✓ ${user.name} (${user.email})`;
    if (authStatus) {
      authStatus.textContent = "Authenticated";
      authStatus.style.background = "rgba(34, 197, 94, 0.2)";
      authStatus.style.color = "#4ade80";
      authStatus.style.borderColor = "rgba(34, 197, 94, 0.4)";
    }
    if (btnManual) btnManual.style.display = "none";
  } else {
    if (badge) badge.style.display = "none";
    if (authStatus) {
      authStatus.textContent = "Not Signed In";
      authStatus.style.background = "rgba(148, 163, 184, 0.2)";
      authStatus.style.color = "#94a3b8";
      authStatus.style.borderColor = "rgba(148, 163, 184, 0.3)";
    }
    if (btnManual) btnManual.style.display = "inline-flex";
  }

  updateSubmitButtonState();
}

/**
 * Clears authentication.
 */
function clearGoogleAuth() {
  localStorage.removeItem("gt_contributor_name");
  localStorage.removeItem("gt_contributor_email");
  setAuthenticatedUser(null);
}

/**
 * Parses and verifies selected telemetry JSON file.
 * @param {File} file
 */
async function handleFileSelected(file) {
  const statusDiv = document.getElementById("pr-submission-status");
  const previewCard = document.getElementById("telemetry-file-preview");

  if (!file.name.toLowerCase().endsWith(".json")) {
    showToast("Please select a valid .json telemetry profile file", "error");
    return;
  }

  try {
    const text = await file.text();
    const data = JSON.parse(text);

    const trackId = data.track_id || data.track;
    const carId = data.car_id || data.car;
    const layout = data.track_layout || data.layout || "";
    const samples = Array.isArray(data.trajectory) ? data.trajectory : (Array.isArray(data.samples) ? data.samples : []);

    if (!trackId || !carId) {
      showToast("File missing track_id or car_id identifier", "error");
      return;
    }

    if (samples.length < 10) {
      showToast(`Trajectory too short: found ${samples.length} samples (expected > 10)`, "error");
      return;
    }

    // Compute metrics
    let maxSpeed = 0;
    let lapTime = Number(data.lap_time_s || data.gold_time || 0);
    for (const s of samples) {
      const spd = Number(s.speed_kmh || 0);
      if (spd > maxSpeed) maxSpeed = spd;
      if (s.t && Number(s.t) > lapTime) lapTime = Number(s.t);
    }

    parsedTelemetry = {
      filename: file.name,
      data,
      trackId,
      carId,
      layout,
      sampleCount: samples.length,
      maxSpeed: Math.round(maxSpeed * 10) / 10,
      lapTime: Math.round(lapTime * 100) / 100,
    };

    // Render Preview Card
    if (previewCard) {
      previewCard.style.display = "block";
      document.getElementById("preview-filename").textContent = file.name;
      document.getElementById("preview-track").textContent = trackId;
      document.getElementById("preview-layout").textContent = layout || "(default)";
      document.getElementById("preview-car").textContent = carId;
      document.getElementById("preview-samples").textContent = `${samples.length.toLocaleString()} pts`;
      document.getElementById("preview-top-speed").textContent = `${parsedTelemetry.maxSpeed} km/h`;
      document.getElementById("preview-lap-time").textContent = `${parsedTelemetry.lapTime}s`;
    }

    showToast(`Validated telemetry for ${carId} @ ${trackId}!`, "success");
    updateSubmitButtonState();

  } catch (err) {
    parsedTelemetry = null;
    if (previewCard) previewCard.style.display = "none";
    showToast(`Failed to parse JSON file: ${err.message}`, "error");
    updateSubmitButtonState();
  }
}

/**
 * Enable or disable the Submit PR button based on readiness.
 */
function updateSubmitButtonState() {
  const btnSubmit = document.getElementById("btn-submit-telemetry-pr");
  if (!btnSubmit) return;

  const isReady = Boolean(googleUser) && Boolean(parsedTelemetry);
  btnSubmit.disabled = !isReady;
}

/**
 * Execute the submission to the serverless PR gateway.
 */
async function executeSubmitPR() {
  if (!googleUser || !parsedTelemetry) {
    showToast("Please sign in and select a valid telemetry file", "warning");
    return;
  }

  const btnSubmit = document.getElementById("btn-submit-telemetry-pr");
  const statusDiv = document.getElementById("pr-submission-status");
  const successCard = document.getElementById("pr-success-card");
  const prLinkBtn = document.getElementById("pr-link-btn");

  if (btnSubmit) {
    btnSubmit.disabled = true;
    btnSubmit.innerHTML = "<span>⏳ Submitting Pull Request...</span>";
  }

  if (statusDiv) {
    statusDiv.style.display = "block";
    statusDiv.style.background = "rgba(56, 189, 248, 0.1)";
    statusDiv.style.border = "1px solid rgba(56, 189, 248, 0.25)";
    statusDiv.style.color = "#38bdf8";
    statusDiv.innerHTML = "<span>Authenticating & communicating with GitHub API...</span>";
  }

  try {
    const res = await api.submitTelemetryProfile({
      googleToken: googleUser.token,
      filename: parsedTelemetry.filename,
      telemetryData: {
        ...parsedTelemetry.data,
        contributor_name: googleUser.name,
        contributor_email: googleUser.email,
      },
    });

    if (res?.success) {
      if (statusDiv) statusDiv.style.display = "none";
      if (successCard && prLinkBtn) {
        successCard.style.display = "block";
        prLinkBtn.href = res.pr_url;
      }
      showToast(`🎉 Pull Request #${res.pr_number} created successfully!`, "success");
      if (btnSubmit) {
        btnSubmit.innerHTML = "<span>✓ Pull Request Created!</span>";
      }
    } else {
      throw new Error(res?.error || "Gateway returned failure");
    }

  } catch (err) {
    if (statusDiv) {
      statusDiv.style.display = "block";
      statusDiv.style.background = "rgba(239, 68, 68, 0.1)";
      statusDiv.style.border = "1px solid rgba(239, 68, 68, 0.3)";
      statusDiv.style.color = "#ef4444";
      statusDiv.innerHTML = `<strong>Submission Error:</strong> ${escapeHtml(err.message)}`;
    }
    showToast(`Error creating PR: ${err.message}`, "error");
    if (btnSubmit) {
      btnSubmit.disabled = false;
      btnSubmit.innerHTML = "<span>Submit Pull Request</span>";
    }
  }
}
