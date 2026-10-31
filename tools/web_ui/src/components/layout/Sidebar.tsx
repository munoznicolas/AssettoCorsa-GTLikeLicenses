import React, { useState, useRef, useEffect } from "react";
import { Plus, ChevronLeft, GripVertical } from "lucide-react";
import { useCurriculum } from "../../context/CurriculumContext";

interface Props {
  onSelectTest?: () => void;
}

export const Sidebar: React.FC<Props> = ({ onSelectTest }) => {
  const { activeTier, activeTestIndex, selectTest, addTestToActiveTier, reorderTestsInActiveTier } =
    useCurriculum();
  const [collapsed, setCollapsed] = useState(false);

  // Drag and drop / Touch-and-hold reorder state
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [dropIndex, setDropIndex] = useState<number | null>(null);
  const isDraggingRef = useRef(false);
  const dragIndexRef = useRef<number | null>(null);
  const dropIndexRef = useRef<number | null>(null);
  const touchTimerRef = useRef<NodeJS.Timeout | null>(null);
  const touchStartPosRef = useRef<{ x: number; y: number } | null>(null);
  const didDragRef = useRef(false);
  const listRef = useRef<HTMLDivElement | null>(null);

  // Touch and hold listener for mobile reordering
  const handleTouchStart = (idx: number, e: React.TouchEvent) => {
    if (collapsed) return;
    const touch = e.touches[0];
    touchStartPosRef.current = { x: touch.clientX, y: touch.clientY };
    didDragRef.current = false;

    if (touchTimerRef.current) {
      clearTimeout(touchTimerRef.current);
    }

    touchTimerRef.current = setTimeout(() => {
      isDraggingRef.current = true;
      dragIndexRef.current = idx;
      dropIndexRef.current = idx;
      didDragRef.current = true;
      setDragIndex(idx);
      setDropIndex(idx);

      if (typeof navigator !== "undefined" && navigator.vibrate) {
        try {
          navigator.vibrate(40);
        } catch (_) {}
      }
    }, 280);
  };

  const handleTouchMoveEarly = (e: React.TouchEvent) => {
    // If not yet entered drag mode, check if user is scrolling normally
    if (!isDraggingRef.current && touchStartPosRef.current) {
      const touch = e.touches[0];
      const dist = Math.hypot(
        touch.clientX - touchStartPosRef.current.x,
        touch.clientY - touchStartPosRef.current.y
      );
      if (dist > 8 && touchTimerRef.current) {
        clearTimeout(touchTimerRef.current);
        touchTimerRef.current = null;
      }
    }
  };

  const handleTouchEndEarly = () => {
    if (touchTimerRef.current) {
      clearTimeout(touchTimerRef.current);
      touchTimerRef.current = null;
    }
  };

  // Active touch drag movement and release listener
  useEffect(() => {
    if (dragIndex === null) return;

    const onWindowTouchMove = (e: TouchEvent) => {
      if (!isDraggingRef.current) return;
      if (e.cancelable) {
        e.preventDefault();
      }

      const touch = e.touches[0];
      const elem = document.elementFromPoint(touch.clientX, touch.clientY);
      const itemElem = elem?.closest(".test-item") as HTMLElement | null;

      if (itemElem && itemElem.dataset.testIndex !== undefined) {
        const targetIdx = parseInt(itemElem.dataset.testIndex, 10);
        if (!isNaN(targetIdx) && targetIdx !== dropIndexRef.current) {
          dropIndexRef.current = targetIdx;
          setDropIndex(targetIdx);
        }
      }

      if (listRef.current) {
        const rect = listRef.current.getBoundingClientRect();
        if (touch.clientY < rect.top + 45) {
          listRef.current.scrollTop -= 8;
        } else if (touch.clientY > rect.bottom - 45) {
          listRef.current.scrollTop += 8;
        }
      }
    };

    const onWindowTouchEnd = () => {
      if (isDraggingRef.current) {
        const from = dragIndexRef.current;
        const to = dropIndexRef.current;
        if (from !== null && to !== null && from !== to) {
          reorderTestsInActiveTier(from, to);
        }
        isDraggingRef.current = false;
        dragIndexRef.current = null;
        dropIndexRef.current = null;
        setDragIndex(null);
        setDropIndex(null);

        setTimeout(() => {
          didDragRef.current = false;
        }, 120);
      }
      if (touchTimerRef.current) {
        clearTimeout(touchTimerRef.current);
        touchTimerRef.current = null;
      }
    };

    window.addEventListener("touchmove", onWindowTouchMove, { passive: false });
    window.addEventListener("touchend", onWindowTouchEnd);
    window.addEventListener("touchcancel", onWindowTouchEnd);

    return () => {
      window.removeEventListener("touchmove", onWindowTouchMove);
      window.removeEventListener("touchend", onWindowTouchEnd);
      window.removeEventListener("touchcancel", onWindowTouchEnd);
    };
  }, [dragIndex, reorderTestsInActiveTier]);

  // Desktop HTML5 drag-and-drop
  const handleDragStart = (idx: number, e: React.DragEvent) => {
    if (collapsed) return;
    e.dataTransfer.setData("text/plain", `${idx}`);
    e.dataTransfer.effectAllowed = "move";
    dragIndexRef.current = idx;
    dropIndexRef.current = idx;
    setDragIndex(idx);
    setDropIndex(idx);
    didDragRef.current = true;
  };

  const handleDragOver = (idx: number, e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (dropIndex !== idx) {
      dropIndexRef.current = idx;
      setDropIndex(idx);
    }
  };

  const handleDrop = (idx: number, e: React.DragEvent) => {
    e.preventDefault();
    const from = dragIndexRef.current;
    if (from !== null && from !== idx) {
      reorderTestsInActiveTier(from, idx);
    }
    setDragIndex(null);
    setDropIndex(null);
    dragIndexRef.current = null;
    dropIndexRef.current = null;
    setTimeout(() => {
      didDragRef.current = false;
    }, 120);
  };

  const handleDragEnd = () => {
    setDragIndex(null);
    setDropIndex(null);
    dragIndexRef.current = null;
    dropIndexRef.current = null;
    setTimeout(() => {
      didDragRef.current = false;
    }, 120);
  };

  if (!activeTier) return null;

  return (
    <aside id="sidebar" className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="sidebar-header">
        <div className="tier-info">
          <h2 id="active-tier-title">{activeTier.name}</h2>
          <span id="test-count-badge" className="badge">
            {activeTier.tests.length} Tests
          </span>
          {dragIndex !== null && (
            <span className="badge reorder-active-badge">Reordering</span>
          )}
        </div>
        <div className="sidebar-header-actions">
          <button
            id="btn-add-test"
            type="button"
            className="btn btn-sm btn-secondary"
            title="Add new test to this license"
            onClick={addTestToActiveTier}
          >
            <Plus size={13} strokeWidth={2.2} className="btn-icon-svg" />
            <span className="btn-text">Add Test</span>
          </button>
          <button
            type="button"
            id="btn-toggle-sidebar"
            className="btn btn-sm btn-secondary btn-icon-only"
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => setCollapsed(!collapsed)}
          >
            <ChevronLeft
              size={14}
              strokeWidth={2.5}
              style={{
                transform: collapsed ? "rotate(180deg)" : "none",
                transition: "transform 0.2s ease",
              }}
            />
          </button>
        </div>
      </div>

      {!collapsed && activeTier.description && (
        <p id="active-tier-desc" className="tier-description">
          {activeTier.description}
        </p>
      )}

      <div
        id="test-list"
        ref={listRef}
        className={`test-list ${dragIndex !== null ? "is-reordering" : ""}`}
      >
        {activeTier.tests.map((test, idx) => {
          const isActive = idx === activeTestIndex;
          const isDragging = idx === dragIndex;
          const isDropTarget = dragIndex !== null && idx === dropIndex && idx !== dragIndex;
          const dropPosition = isDropTarget && dragIndex !== null
            ? idx < dragIndex
              ? "drop-target-above"
              : "drop-target-below"
            : "";
          const modeClass = test.start_mode?.toLowerCase() || "standing";

          return (
            <div
              key={test.test_id || idx}
              data-test-index={idx}
              draggable={!collapsed}
              className={`test-item ${isActive ? "active" : ""} ${
                isDragging ? "drag-active" : ""
              } ${dropPosition}`}
              onTouchStart={(e) => handleTouchStart(idx, e)}
              onTouchMove={handleTouchMoveEarly}
              onTouchEnd={handleTouchEndEarly}
              onTouchCancel={handleTouchEndEarly}
              onDragStart={(e) => handleDragStart(idx, e)}
              onDragOver={(e) => handleDragOver(idx, e)}
              onDrop={(e) => handleDrop(idx, e)}
              onDragEnd={handleDragEnd}
              onClick={() => {
                if (didDragRef.current) return;
                selectTest(idx);
                onSelectTest?.();
              }}
            >
              <div className="test-item-thumb">
                {test.preview_image ? (
                  <img src={test.preview_image} alt={test.test_id} loading="lazy" />
                ) : (
                  <span style={{ fontSize: "11px", color: "var(--text-dim)", fontFamily: "var(--font-mono)" }}>
                    {test.test_id}
                  </span>
                )}
                <span className="test-item-stage-overlay">{test.test_id}</span>
              </div>

              {!collapsed && (
                <div className="test-item-body">
                  <div className="test-item-top">
                    <span className="test-item-id">{test.test_id}</span>
                    <span className={`test-item-mode ${modeClass}`}>{test.start_mode}</span>
                  </div>
                  <div className="test-item-title">{test.title}</div>
                  <div className="test-item-meta">
                    <span>{test.track_id}</span>
                  </div>
                </div>
              )}

              {!collapsed && (
                <div className="test-item-drag-handle" title="Hold or drag to reorder">
                  <GripVertical size={14} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </aside>
  );
};
