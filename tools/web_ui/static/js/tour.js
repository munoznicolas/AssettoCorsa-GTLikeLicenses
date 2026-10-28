/**
 * tour.js
 * Interactive Onboarding Tours for Assetto Corsa GT License Center.
 * Uses Driver.js for smooth spotlight cutouts and dark cyber GT-themed step guidance.
 */

import { dom } from "./dom.js";
import { isStaticHost } from "./api.js";
import { state } from "./state.js";
import { selectTier, loadTestIntoForm } from "./test-editor.js";
import { showToast } from "./ui-utils.js";

let activeDriver = null;

/**
 * Open the Welcome / Tour Selection Modal.
 */
export function openTourWelcomeModal() {
  if (dom.modalTourWelcome) {
    dom.modalTourWelcome.style.display = "flex";
  }
}

/**
 * Close the Welcome / Tour Selection Modal.
 */
export function closeTourWelcomeModal() {
  if (dom.modalTourWelcome) {
    dom.modalTourWelcome.style.display = "none";
  }
}

/**
 * Ensure the editor is visible and populated with a test (defaults to B-1).
 */
function ensureEditorReady() {
  // Expand sidebar if collapsed
  const sidebar = document.getElementById("sidebar");
  if (sidebar && sidebar.classList.contains("collapsed")) {
    if (typeof window.toggleSidebar === "function") {
      window.toggleSidebar();
    }
  }

  // Ensure reference view is closed and workspace is active
  if (dom.workspaceView && dom.workspaceView.style.display === "none") {
    selectTier(0);
  }

  // Load test 0 if empty
  if (state.curriculum && state.curriculum.length > 0) {
    const tierIdx = state.activeTierIndex ?? 0;
    const testIdx = state.activeTestIndex ?? 0;
    const activeTier = state.curriculum[tierIdx];
    if (activeTier && activeTier.tests && activeTier.tests.length > 0) {
      void loadTestIntoForm(testIdx);
    }
  }
}

/**
 * Launch Flow 1: Modifying an Existing Test.
 */
export function startEditTestTour() {
  closeTourWelcomeModal();
  ensureEditorReady();

  if (!window.driver?.js?.driver) {
    showToast("Tour engine not loaded.", "error");
    return;
  }

  const driver = window.driver.js.driver;
  activeDriver = driver({
    showProgress: true,
    animate: true,
    overlayOpacity: 0.78,
    stagePadding: 8,
    stageRadius: 6,
    allowClose: true,
    doneBtnText: "Finish Tour",
    nextBtnText: "Next →",
    prevBtnText: "← Back",
    progressText: "Step {{current}} of {{total}}",
    onDestroyed: () => {
      localStorage.setItem("gt_tour_completed", "true");
      activeDriver = null;
    },
    steps: [
      {
        element: "#license-tabs",
        popover: {
          title: "License Tiers",
          description: "Gran Turismo driving school tests are grouped across 5 progressive tiers (National B up to Super License). Click any tab to switch license categories.",
          side: "bottom",
          align: "start"
        }
      },
      {
        element: "#sidebar",
        popover: {
          title: "Curriculum Tests",
          description: "Each tier contains dedicated driving school tests. Select any test from this sidebar to load it into the editor, or click <strong>+ Add Test</strong> to create a new curriculum test.",
          side: "right",
          align: "start"
        }
      },
      {
        element: "#card-lesson-info",
        popover: {
          title: "Lesson Objective & Description",
          description: "Customize the test title, pedagogical objective, and driver instructions. These briefing notes appear directly on the countdown screen and HUD in Assetto Corsa.",
          side: "bottom",
          align: "start"
        }
      },
      {
        element: "#card-track-vehicle",
        popover: {
          title: "Vehicle & Circuit Selection",
          description: "Assign official Kunos or modded cars and track layouts. The circuit spline provides the underlying racing line geometry for AI autopilot and speed calculation.",
          side: "bottom",
          align: "start"
        }
      },
      {
        element: "#card-gates-spline",
        popover: {
          title: "3D Start & Finish Gates",
          description: "Position the start and finish gates along the track spline using the interactive percentage/distance sliders and 2D track canvas preview.",
          side: "top",
          align: "start"
        }
      },
      {
        element: "#card-target-times",
        popover: {
          title: "Medal Targets (Adjudication)",
          description: "Set the Gold, Silver, and Bronze cutoff times in seconds. In-game, the Lua engine adjudicates sector times, awarding medals and unlocking the next test when target times are met.",
          side: "top",
          align: "start"
        }
      },
      {
        element: ".form-actions",
        popover: {
          title: isStaticHost() ? "Save & Export" : "Save, Test Drive & Sync",
          description: isStaticHost()
            ? "Click <strong>Save Test</strong> to persist changes. Use <strong>Export</strong> in the navbar to generate a ready-to-install Content Manager package (.zip)!"
            : "Click <strong>Save Test</strong> to persist changes. Use <strong>Watch AI Demo</strong> to verify the test live in Assetto Corsa, and <strong>Sync to AC</strong> in the navbar to deploy directly to Content Manager!",
          side: "bottom",
          align: "end"
        }
      }
    ]
  });

  activeDriver.drive();
}

/**
 * Launch Flow 2: Generated Scripts for Car+Track Combinations Without Data.
 */
export function startMissingTelemetryTour() {
  closeTourWelcomeModal();
  ensureEditorReady();

  if (!window.driver?.js?.driver) {
    showToast("Tour engine not loaded.", "error");
    return;
  }

  // Temporarily ensure the Missing Telemetry Card is visible so the spotlight can highlight it
  const wasMissingVisible = dom.telemetryMissingCard && dom.telemetryMissingCard.style.display !== "none";
  if (dom.telemetryMissingCard) {
    dom.telemetryMissingCard.style.display = "block";
  }
  if (dom.btnExportSingleTelemetryScript) {
    dom.btnExportSingleTelemetryScript.style.display = "inline-flex";
  }

  const driver = window.driver.js.driver;
  activeDriver = driver({
    showProgress: true,
    animate: true,
    overlayOpacity: 0.78,
    stagePadding: 8,
    stageRadius: 6,
    allowClose: true,
    doneBtnText: "Finish Tour",
    nextBtnText: "Next →",
    prevBtnText: "← Back",
    progressText: "Step {{current}} of {{total}}",
    onDestroyed: () => {
      // Restore card state
      if (!wasMissingVisible && dom.telemetryMissingCard) {
        dom.telemetryMissingCard.style.display = "none";
      }
      localStorage.setItem("gt_tour_completed", "true");
      activeDriver = null;
    },
    steps: [
      {
        element: "#telemetry-missing-card",
        popover: {
          title: "Missing AI Telemetry Alert",
          description: "Rolling starts and medal target calibrations require AI racing line telemetry. When a test's car + track combination has no pre-recorded data, this warning card appears automatically.",
          side: "top",
          align: "start"
        }
      },
      {
        element: "#btn-download-record-script",
        popover: {
          title: "Download Recording Script (.ps1)",
          description: "Click here to download an automated PowerShell runner script tailored specifically for this car and track combination.",
          side: "bottom",
          align: "end"
        }
      },
      {
        element: "#telemetry-missing-card",
        popover: {
          title: "Run Script in Assetto Corsa",
          description: "Run the downloaded PowerShell script in your terminal:<br><code style=\"color:#38bdf8;background:rgba(0,0,0,0.4);padding:3px 8px;border-radius:4px;display:inline-block;margin:6px 0;font-size:12px;\">.\\record_telemetry_*.ps1</code><br>Assetto Corsa will launch with native AI autopilot, drive the circuit spline, and record the ideal racing line profile to a JSON file.",
          side: "top",
          align: "center"
        }
      },
      {
        element: "#telemetry-dropzone-editor",
        popover: {
          title: "Drag & Drop Recorded Profile",
          description: "Once Assetto Corsa completes recording, drag and drop the generated <code>.json</code> file into this dropzone. The web studio immediately calculates entry speed, initial gears, and medal targets!",
          side: "top",
          align: "center"
        }
      },
      {
        element: isStaticHost() ? "#btn-open-submit-pr-modal" : "#btn-sync",
        popover: {
          title: isStaticHost() ? "Share & Contribute (GitHub PR)" : "Sync to Assetto Corsa",
          description: isStaticHost()
            ? "Once your profile is tested, click <strong>Submit Telemetry (PR)</strong> to automatically submit your recording to the community catalog via a GitHub Pull Request!"
            : "Once your profile is tested, click <strong>Sync to AC</strong> in the navbar to deploy the updated telemetry directly to Content Manager!",
          side: "bottom",
          align: isStaticHost() ? "start" : "end"
        }
      }
    ]
  });

  activeDriver.drive();
}

/**
 * Initialize Tour Module listeners and check first-time visitor state.
 */
export function initTour() {
  if (dom.btnTourHelp) {
    dom.btnTourHelp.addEventListener("click", openTourWelcomeModal);
  }
  if (dom.modalTourClose) {
    dom.modalTourClose.addEventListener("click", closeTourWelcomeModal);
  }
  if (dom.btnSkipTour) {
    dom.btnSkipTour.addEventListener("click", () => {
      localStorage.setItem("gt_tour_completed", "true");
      closeTourWelcomeModal();
    });
  }
  if (dom.btnStartTourEdit) {
    dom.btnStartTourEdit.addEventListener("click", startEditTestTour);
  }
  if (dom.btnStartTourTelemetry) {
    dom.btnStartTourTelemetry.addEventListener("click", startMissingTelemetryTour);
  }

  // Outside click to close welcome modal
  window.addEventListener("click", (e) => {
    if (e.target === dom.modalTourWelcome) {
      closeTourWelcomeModal();
    }
  });

  // Check first-time visitor status
  try {
    const hasSeenTour = localStorage.getItem("gt_tour_completed");
    if (!hasSeenTour) {
      // Auto-open welcome modal with a brief delay after UI rendering
      setTimeout(() => {
        openTourWelcomeModal();
      }, 700);
    }
  } catch (e) {
    console.warn("Tour localStorage check error:", e);
  }
}
