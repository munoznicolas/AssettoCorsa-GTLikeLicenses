import React from "react";
import { Autocomplete, TextField, Box, Typography } from "@mui/material";
import { Track, CarModel } from "../../types";

interface Props {
  tracks: Track[];
  cars: CarModel[];
  selectedTrackId: string;
  selectedLayout: string;
  selectedCarId: string;
  onTrackChange: (trackId: string) => void;
  onLayoutChange: (layout: string) => void;
  onCarChange: (carId: string) => void;
}

export const TrackVehicleSection: React.FC<Props> = ({
  tracks,
  cars,
  selectedTrackId,
  selectedLayout,
  selectedCarId,
  onTrackChange,
  onLayoutChange,
  onCarChange,
}) => {
  const currentTrack = tracks.find((t) => t.track_id === selectedTrackId) || null;
  const currentCar = cars.find((c) => c.car_id === selectedCarId) || null;
  const layouts = currentTrack?.layouts || [];

  // Determine current selected layout
  const currentLayoutObj = layouts.find((l) => {
    const id = typeof l === "string" ? l : l.layout_id || "";
    return id === selectedLayout;
  }) || null;

  return (
    <div className="card form-card">
      <div className="card-title">
        <span>Track & Vehicle Selection</span>
      </div>

      <div className="form-grid cols-3" style={{ gap: "14px", alignItems: "flex-start" }}>
        {/* 1. Track Autocomplete */}
        <div className="form-group">
          <Autocomplete
            options={tracks}
            getOptionLabel={(option) => {
              if (!option) return "";
              if (!option.name || option.name.toLowerCase().trim() === option.track_id.toLowerCase().trim()) {
                return option.name || option.track_id;
              }
              return `${option.name} (${option.track_id})`;
            }}
            isOptionEqualToValue={(option, val) => option.track_id === val.track_id}
            value={currentTrack}
            onChange={(_, newValue) => {
              const newTrackId = newValue?.track_id || "";
              onTrackChange(newTrackId);
            }}
            filterOptions={(options, state) => {
              const query = state.inputValue.toLowerCase().trim();
              if (!query) return options;
              return options.filter(
                (t) =>
                  t.name.toLowerCase().includes(query) ||
                  t.track_id.toLowerCase().includes(query)
              );
            }}
            renderOption={(props, option) => {
              const { key, ...otherProps } = props as { key: React.Key; [k: string]: unknown };
              const isSame =
                !option.track_id ||
                option.name.toLowerCase().trim() === option.track_id.toLowerCase().trim();
              return (
                <Box
                  component="li"
                  key={key}
                  {...otherProps}
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 1.5,
                    width: "100%",
                  }}
                >
                  <span style={{ fontWeight: 500 }}>{option.name}</span>
                  {!isSame && (
                    <Typography
                      variant="caption"
                      sx={{
                        color: "text.secondary",
                        fontFamily: "var(--font-mono)",
                        fontSize: "11px",
                        flexShrink: 0,
                      }}
                    >
                      {option.track_id}
                    </Typography>
                  )}
                </Box>
              );
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Track (Kunos)"
                placeholder="Search tracks..."
                size="small"
                InputLabelProps={{ shrink: true }}
              />
            )}
          />
        </div>

        {/* 2. Track Layout Autocomplete */}
        <div className="form-group">
          <Autocomplete
            options={layouts}
            getOptionLabel={(option) => {
              if (typeof option === "string") {
                return option ? option.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()) : "Default Layout";
              }
              return option.name || option.layout_id || "Default Layout";
            }}
            isOptionEqualToValue={(option, val) => {
              const optId = typeof option === "string" ? option : option.layout_id || "";
              const valId = typeof val === "string" ? val : val.layout_id || "";
              return optId === valId;
            }}
            value={currentLayoutObj}
            disabled={layouts.length <= 1}
            onChange={(_, newValue) => {
              if (!newValue) {
                onLayoutChange("");
                return;
              }
              const id = typeof newValue === "string" ? newValue : newValue.layout_id || "";
              onLayoutChange(id);
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Layout"
                placeholder={layouts.length <= 1 ? "Default Layout (Single)" : "Select layout..."}
                size="small"
                InputLabelProps={{ shrink: true }}
              />
            )}
          />
        </div>

        {/* 3. Car Model Autocomplete with multi-token search */}
        <div className="form-group">
          <Autocomplete
            options={cars}
            getOptionLabel={(option) => (option ? option.name : "")}
            isOptionEqualToValue={(option, val) => option.car_id === val.car_id}
            value={currentCar}
            onChange={(_, newValue) => {
              onCarChange(newValue?.car_id || "");
            }}
            filterOptions={(options, state) => {
              const tokens = state.inputValue.toLowerCase().split(/\s+/).filter(Boolean);
              if (tokens.length === 0) return options;
              return options.filter((car) => {
                const combined = `${car.name} ${car.brand || ""} ${car.car_id} ${car.drivetrain || ""} ${(car.tags || []).join(" ")}`.toLowerCase();
                return tokens.every((tok) => combined.includes(tok));
              });
            }}
            renderOption={(props, option) => {
              const { key, ...otherProps } = props as { key: React.Key; [k: string]: unknown };
              return (
                <Box
                  component="li"
                  key={key}
                  {...otherProps}
                  sx={{ display: "flex", alignItems: "center", width: "100%", py: 0.5 }}
                >
                  <span>{option.name}</span>
                  {option.drivetrain && (
                    <span
                      className="badge"
                      style={{
                        fontSize: "10px",
                        padding: "1px 6px",
                        marginLeft: "8px",
                        flexShrink: 0,
                      }}
                    >
                      {option.drivetrain.toUpperCase()}
                    </span>
                  )}
                </Box>
              );
            }}
            renderInput={(params) => (
              <TextField
                {...params}
                label="Car Model (Kunos)"
                placeholder="Search model, brand, drivetrain..."
                size="small"
                InputLabelProps={{ shrink: true }}
              />
            )}
          />
        </div>
      </div>
    </div>
  );
};
