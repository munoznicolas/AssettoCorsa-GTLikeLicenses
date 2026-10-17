/**
 * editor/sidebar.js
 * License tier tabs, test list rendering, and drag-and-drop test reordering.
 */

import { state } from "../state.js";
import { dom } from "../dom.js";
import { showToast, escapeHtml } from "../ui-utils.js";
import {
  isFullLapTest,
  loadTestIntoForm,
  clearForm,
  saveFormIntoActiveTest,
  saveCurrentTier,
} from "../test-editor.js";

let draggedTestItem = null;
let testOrderChangedDuringDrag = false;
let testDropHandled = false;
let suppressTestClickUntil = 0;

/**
 * Render license tier navigation tabs.
 */
export function renderLicenseTabs() {
  if (!dom.tabsContainer) return;
  dom.tabsContainer.innerHTML = "";
  state.curriculum.forEach((tier, idx) => {
    const btn = document.createElement("button");
    btn.className = `license-tab ${idx === state.activeTierIndex ? "active" : ""}`;
    btn.innerHTML = `
      <img class="tab-badge-img" src="/assets/career_ui/${escapeHtml(tier.badge_asset)}" alt="${escapeHtml(tier.name)}">
      <span>${escapeHtml(tier.tier_name)}</span>
      <span class="tab-count">${Number(tier.tests.length) || 0}</span>
    `;
    btn.addEventListener("click", () => selectTier(idx));
    dom.tabsContainer.appendChild(btn);
  });
}

/**
 * Switch active license tier.
 */
export function selectTier(tierIdx) {
  state.activeTierIndex = tierIdx;
  state.activeTestIndex = 0;
  state.isReferenceViewActive = false;

  // Show workspace, hide reference view
  if (dom.workspaceView) dom.workspaceView.style.display = "flex";
  if (dom.referenceView) dom.referenceView.style.display = "none";
  if (dom.tabBtnReference) dom.tabBtnReference.classList.remove("active");

  // Update active tab styling
  document.querySelectorAll(".tab-container .license-tab").forEach((tab, idx) => {
    tab.classList.toggle("active", idx === tierIdx);
  });

  const activeTier = state.curriculum[tierIdx];
  if (!activeTier) return;

  if (dom.tierTitle) dom.tierTitle.textContent = activeTier.tier_name;
  if (dom.tierDesc) dom.tierDesc.textContent = activeTier.description;
  if (dom.testCountBadge) dom.testCountBadge.textContent = `${activeTier.tests.length} Tests`;

  renderTestList();
  if (activeTier.tests.length > 0) {
    void loadTestIntoForm(0);
  } else {
    clearForm();
  }
}

/**
 * Render tests sidebar list for the active tier.
 */
export function renderTestList() {
  if (!dom.testList) return;
  dom.testList.innerHTML = "";
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier) return;

  activeTier.tests.forEach((test, idx) => {
    const item = document.createElement("div");
    item.className = `test-item ${idx === state.activeTestIndex ? "active" : ""}`;
    item.draggable = true;
    item.dataset.testIndex = String(idx);
    item.title = "Drag to reorder tests";

    const modeClass = escapeHtml((test.start_mode || "standing").toLowerCase());
    const isFullLap = isFullLapTest(test);
    const lapTypeLabel = isFullLap ? "Full Lap" : "Sector";

    const previewUrl =
      test.preview_image ||
      (activeTier.folder
        ? `/content/career/${encodeURIComponent(activeTier.folder)}/event${idx + 1}/preview.png`
        : `/api/test_preview?test_id=${encodeURIComponent(test.test_id)}`);

    item.innerHTML = `
      <span class="test-item-drag-handle" aria-hidden="true"></span>
      <div class="test-item-thumb">
        <img src="${escapeHtml(previewUrl)}?t=${encodeURIComponent(state.cacheBuster)}" 
             alt="${escapeHtml(test.test_id)}" 
             loading="lazy" 
             onerror="this.parentElement.style.opacity='0.25'; this.style.display='none'">
      </div>
      <div class="test-item-body">
        <div class="test-item-top">
          <span class="test-item-id">${escapeHtml(test.test_id)}</span>
          <span class="test-item-mode ${modeClass}">${escapeHtml(test.start_mode)}</span>
        </div>
        <div class="test-item-title">${escapeHtml(test.title)}</div>
        <div class="test-item-meta">
          <span>🏁 ${lapTypeLabel}</span>
          <span>📍 ${escapeHtml(test.track_id)}</span>
          <span>🥇 ${test.targets?.gold_seconds !== undefined ? `${Number(test.targets.gold_seconds).toFixed(2)}s` : ""}</span>
        </div>
      </div>
    `;

    item.addEventListener("click", () => {
      if (Date.now() < suppressTestClickUntil) return;
      void loadTestIntoForm(idx);
    });
    item.addEventListener("dragstart", (event) => {
      draggedTestItem = item;
      testOrderChangedDuringDrag = false;
      testDropHandled = false;
      item.classList.add("dragging");
      if (event.dataTransfer) {
        event.dataTransfer.effectAllowed = "move";
        event.dataTransfer.setData("text/plain", String(idx));
      }
    });
    item.addEventListener("dragend", () => {
      item.classList.remove("dragging");
      if (testOrderChangedDuringDrag && !testDropHandled) renderTestList();
      draggedTestItem = null;
      testOrderChangedDuringDrag = false;
      testDropHandled = false;
    });
    dom.testList.appendChild(item);
  });
}

/**
 * Persist the visual order of test cards as the active tier's new test order.
 */
export async function saveDraggedTestOrder() {
  const activeTier = state.curriculum[state.activeTierIndex];
  if (!activeTier?.tests || !draggedTestItem) return;

  const previousOrder = activeTier.tests.slice();
  const reorderedTests = Array.from(dom.testList.querySelectorAll(".test-item")).map(
    (item) => previousOrder[Number(item.dataset.testIndex)]
  );
  if (
    reorderedTests.length !== previousOrder.length ||
    reorderedTests.some((test) => !test) ||
    reorderedTests.every((test, index) => test === previousOrder[index])
  ) {
    renderTestList();
    return;
  }

  saveFormIntoActiveTest();
  const selectedTest = activeTier.tests[state.activeTestIndex];
  const originalIds = new Map(
    previousOrder.map((test) => [
      test,
      {
        test_id: test.test_id,
        previous_test_id: test.previous_test_id,
        preview_image: test.preview_image,
      },
    ])
  );

  activeTier.tests.splice(0, activeTier.tests.length, ...reorderedTests);
  renumberTierTests(activeTier, { updatePreviewPaths: false });
  state.activeTestIndex = activeTier.tests.indexOf(selectedTest);
  suppressTestClickUntil = Date.now() + 300;
  renderTestList();

  try {
    await saveCurrentTier();
    renumberTierTests(activeTier, { updatePreviewPaths: true });
    for (const test of activeTier.tests) {
      delete test.previous_test_id;
    }
    state.cacheBuster = Date.now();
    renderTestList();
    await loadTestIntoForm(state.activeTestIndex);
    showToast(`Tests reordered and renumbered in ${activeTier.tier_name}.`);
  } catch (err) {
    activeTier.tests.splice(0, activeTier.tests.length, ...previousOrder);
    for (const test of previousOrder) {
      const original = originalIds.get(test);
      test.test_id = original.test_id;
      if (original.previous_test_id === undefined) {
        delete test.previous_test_id;
      } else {
        test.previous_test_id = original.previous_test_id;
      }
      if (original.preview_image === undefined) {
        delete test.preview_image;
      } else {
        test.preview_image = original.preview_image;
      }
    }
    state.activeTestIndex = activeTier.tests.indexOf(selectedTest);
    renderTestList();
    await loadTestIntoForm(state.activeTestIndex);
    showToast(`Could not save test order: ${err.message}`, "error");
  }
}

/**
 * Renumber test IDs and preview image paths sequentially within a tier.
 */
export function renumberTierTests(tier, { updatePreviewPaths = true } = {}) {
  if (!tier?.tests) return;
  const prefix = tier.test_prefix || "T-";
  tier.tests.forEach((t, i) => {
    const num = i + 1;
    if (t.previous_test_id === undefined && t.test_id) {
      t.previous_test_id = t.test_id;
    }
    t.test_id = `${prefix}${num}`;
    if (updatePreviewPaths && tier.folder) {
      t.preview_image = `/content/career/${tier.folder}/event${num}/preview.png`;
    }
  });
}

/**
 * Attach dragover and drop listeners on the test list container.
 */
export function setupTestListDragListeners() {
  dom.testList?.addEventListener("dragover", (event) => {
    if (!draggedTestItem) return;
    event.preventDefault();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "move";

    const targetItem = event.target instanceof Element
      ? event.target.closest(".test-item")
      : null;
    if (!targetItem) {
      if (event.target === dom.testList && draggedTestItem.nextSibling) {
        dom.testList.appendChild(draggedTestItem);
        testOrderChangedDuringDrag = true;
      }
      return;
    }
    if (targetItem === draggedTestItem) return;

    const bounds = targetItem.getBoundingClientRect();
    const insertAfter = event.clientY > bounds.top + bounds.height / 2;
    const referenceNode = insertAfter ? targetItem.nextSibling : targetItem;
    if (referenceNode !== draggedTestItem) {
      dom.testList.insertBefore(draggedTestItem, referenceNode);
      testOrderChangedDuringDrag = true;
    }
  });

  dom.testList?.addEventListener("drop", (event) => {
    if (!draggedTestItem) return;
    event.preventDefault();
    event.stopPropagation();
    testDropHandled = true;
    if (testOrderChangedDuringDrag) void saveDraggedTestOrder();
    else renderTestList();
    testOrderChangedDuringDrag = false;
  });
}
