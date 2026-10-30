import React from "react";
import { Menu } from "lucide-react";

interface Props {
  isOpen?: boolean;
  onToggleMenu: () => void;
}

export const Header: React.FC<Props> = ({ isOpen, onToggleMenu }) => {
  return (
    <header className="navbar">
      <div className="brand">
        <img
          src="/favicon.svg"
          alt="License Center Logo"
          className="gt-logo-img"
          width="34"
          height="34"
        />
        <div className="title-wrap">
          <h1>License Center</h1>
          <span className="subtitle">Assetto Corsa Driving School &amp; Telemetry Studio</span>
        </div>
      </div>

      <div className="header-actions-wrapper">
        <button
          type="button"
          id="btn-header-menu"
          className={`btn btn-secondary header-menu-toggle ${isOpen ? "active" : ""}`}
          title={isOpen ? "Close menu" : "Open menu"}
          aria-label={isOpen ? "Close menu" : "Open menu"}
          aria-expanded={isOpen}
          onClick={onToggleMenu}
        >
          <Menu size={16} strokeWidth={2} aria-hidden="true" />
          <span>Menu</span>
        </button>
      </div>
    </header>
  );
};
