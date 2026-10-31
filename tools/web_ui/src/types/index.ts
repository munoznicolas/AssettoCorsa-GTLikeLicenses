export interface Targets {
  gold?: string;
  gold_seconds?: number;
  silver?: string;
  silver_seconds?: number;
  bronze?: string;
  bronze_seconds?: number;
  author?: string;
  author_seconds?: number;
}

export interface LicenseTest {
  test_id: string;
  title: string;
  objective?: string;
  lesson_objective?: string;
  description?: string;
  track_id: string;
  track_layout?: string;
  car_id: string;
  start_mode: "STANDING" | "ROLLING" | "FLYING_LAP";
  start_s?: number;
  finish_s?: number;
  with_stop_box?: boolean;
  spawn_offset_meters?: number;
  spawn_offset?: number;
  rolling_speed_kmh?: number;
  speed?: number;
  initial_gear?: number;
  initial_rpm?: number;
  targets?: Targets;
  preview_image?: string;
  tier?: string;
}

export interface LicenseTier {
  name: string;
  tier_name?: string;
  code?: string;
  folder?: string;
  description?: string;
  badge_asset?: string;
  test_prefix?: string;
  tests: LicenseTest[];
}

export interface TrackLayout {
  layout_id?: string;
  name?: string;
}

export interface Track {
  track_id: string;
  name: string;
  layouts?: (string | TrackLayout)[];
  spline_cached?: boolean;
}

export interface CarModel {
  car_id: string;
  name: string;
  brand?: string;
  drivetrain?: string;
  power_bhp?: number;
  weight_kg?: number;
  tags?: string[];
}

export interface SplinePoint {
  x: number;
  y: number;
  z: number;
  s: number;
  speed?: number;
  throttle?: number;
  brake?: number;
  gear?: number;
  rpm?: number;
}

export interface SplineData {
  track_id: string;
  layout: string;
  points: SplinePoint[];
  total_length_m: number;
}

export interface ReferenceTest {
  game: string;
  code: string;
  tier: string;
  test: string;
  title?: string;
  car: string;
  hp?: number;
  weight?: number;
  pw?: number;
  pw_kg_hp?: number;
  weight_kg?: number;
  layout?: string;
  track: string;
  gold: string;
  silver?: string;
  bronze?: string;
  gold_s?: number;
  gold_seconds?: number;
}

export interface TelemetryMissingCombo {
  track_id: string;
  track_layout: string;
  car_id: string;
  test_count?: number;
  test_ids: string[];
  is_cached?: boolean;
  is_queued?: boolean;
}
