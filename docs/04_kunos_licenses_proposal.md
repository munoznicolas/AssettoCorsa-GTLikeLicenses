# Gran Turismo-Style License Tests Proposal (Kunos Official Resources)

## 1. Executive Summary & Design Framework

This document outlines a complete, production-ready curriculum of **5 License Tiers** comprising **58 individual driving tests**, built **exclusively using official content from *Assetto Corsa: Ultimate Edition*** (Kunos Base Game + all DLCs).

### 1.1 Structural Overview
* **Tier 1: National B License (12 Tests)** — Fundamentals of longitudinal control, braking markers, out-in-out trajectory, and basic drivetrain behaviors in road production cars.
* **Tier 2: National A License (12 Tests)** — Complex multi-corner links, chicanes, blind crests, elevation drop braking (Corkscrew), and managing mid-engine snap oversteer in analog sports cars.
* **Tier 3: International B License (12 Tests)** — High-speed sweepers, aerodynamic downforce, throttle modulation under low traction, slipstream drafting, and modern supercars.
* **Tier 4: International A License (12 Tests)** — Professional motorsport racecraft, full slick tires, anti-lock race braking, aggressive curb jumping, and multi-class GT4/GT3/DTM machinery.
* **Tier 5: Super License (10 Tests)** — Full-circuit time trials with zero margin for error across 10 laser-scanned world circuits in legendary GT, Prototype, and Formula machinery.

### 1.2 Universal Disqualification & Adjudication Rules
Every test in this proposal is monitored under strict Gran Turismo rules:
1. **Off-Track Violation**: More than 2 wheels leaving the asphalt/curb boundary into dirt, grass, or gravel causes an instant **DISQUALIFIED** trigger.
2. **Barrier / Scenery Contact**: Any collision with guardrails, tire walls, concrete barriers, or bridge parapets above a minimal force threshold ($> 1,500\text{ N}$) causes instant failure.
3. **Loss of Control**: A vehicle spin exceeding $90^\circ$ yaw angle relative to the track centerline triggers instant failure.
4. **Stop Box Boundary Compliance**: On acceleration & braking tests, the vehicle must come to a complete standstill ($< 0.5\text{ km/h}$) strictly inside the painted stop box.
5. **Target Expiration**: If the session timer exceeds the Bronze medal threshold, the test terminates immediately.

---

## 2. National B License (12 Tests)

*Entry-level motorsport fundamentals: longitudinal braking perception, traction limits on corner exit, weight transfer across basic chicanes, and low-power momentum conservation.*

**License Rewards**:
* **All Bronze**: `ks_alfa_romeo_mito_qv` (Alfa Romeo MiTo Quadrifoglio Verde)
* **All Gold**: `ks_toyota_gt86` (Toyota GT86)

---

### Test Catalog: National B

#### B-1: 200m Acceleration & Braking (Short Threshold)
* **Car**: Abarth 500 EsseEsse (`abarth500`) | FWD | 160 bhp | 1,025 kg
* **Track / Location**: Drag 200m (`ks_drag` / `drag200`)
* **Start Type**: Standing Start ($0\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:11.200`
  * 🥈 Silver: `0:11.800`
  * 🥉 Bronze: `0:12.800`
* **Objective & Lesson**: Launch cleanly with minimal front wheelspin. Reach peak speed in 3rd gear, anchor eyes on the 150m braking marker, and execute threshold braking to bring the car to a full stop inside the marked grid box without locking the tires or overshooting.

#### B-2: 500m Acceleration & High-Speed Stop
* **Car**: Alfa Romeo Giulietta QV (`alfa_romeo_giulietta_qv`) | FWD | 235 bhp | 1,390 kg
* **Track / Location**: Drag 500m (`ks_drag` / `drag500`)
* **Start Type**: Standing Start ($0\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:18.400`
  * 🥈 Silver: `0:19.100`
  * 🥉 Bronze: `0:20.500`
* **Objective & Lesson**: High-speed braking from 170+ km/h. Managing the heavier 1,390 kg curb weight; braking early enough to avoid triggering ABS wheel hop while stopping fully within the designated box.

#### B-3: Out-In-Out Hairpin Trajectory
* **Car**: Mazda MX-5 Miata NA (`ks_mazda_miata`) | RWD | 115 bhp | 960 kg
* **Track / Location**: Autodromo Vallelunga (`ks_vallelunga` / `club_circuit`) — *Tornantino Hairpin (Turn 4)*
* **Start Type**: Rolling Start ($70\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:13.800`
  * 🥈 Silver: `0:14.500`
  * 🥉 Bronze: `0:15.800`
* **Objective & Lesson**: Approach from the far track edge. Brake in a straight line, clip the rumble strip late at the apex, and open the steering wheel progressively onto the exit straight to preserve rolling momentum in a low-horsepower roadster.

#### B-4: Front-Wheel Drive Understeer Management
* **Car**: Alfa Romeo MiTo QV (`ks_alfa_romeo_mito_qv`) | FWD | 170 bhp | 1,170 kg
* **Track / Location**: Autodromo di Magione (`magione` / `default`) — *Curva del Muro (Turn 7)*
* **Start Type**: Rolling Start ($90\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:12.900`
  * 🥈 Silver: `0:13.500`
  * 🥉 Bronze: `0:14.600`
* **Objective & Lesson**: Understanding that aggressive throttle in FWD pushes the nose wide. Modulate throttle at 40–50% mid-corner until the front tires regain grip, then squeeze full throttle once the wheels are straightened.

#### B-5: Low-Speed Weight Transfer & Transition
* **Car**: Toyota AE86 Trueno (`ks_toyota_ae86`) | RWD | 130 bhp | 950 kg
* **Track / Location**: Silverstone National (`ks_silverstone` / `national`) — *Brooklands to Luffield Complex*
* **Start Type**: Rolling Start ($100\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:19.400`
  * 🥈 Silver: `0:20.200`
  * 🥉 Bronze: `0:21.800`
* **Objective & Lesson**: Managing a classic live-axle rear-wheel drive chassis. Trail-braking into Brooklands, settling the suspension, and smoothly transferring lateral load across into the long looping Luffield radius.

#### B-6: Threshold Braking from 190 km/h into Chicane
* **Car**: BMW M3 E30 (`bmw_m3_e30`) | RWD | 238 bhp | 1,200 kg
* **Track / Location**: Autodromo Nazionale Monza (`monza` / `default`) — *Prima Variante (Turn 1 & 2)*
* **Start Type**: Rolling Start ($180\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:14.800`
  * 🥈 Silver: `0:15.500`
  * 🥉 Bronze: `0:16.800`
* **Objective & Lesson**: Heavy braking at the 150m board down to 60 km/h. Downshifting with rev-matching, hopping the first right curb cleanly without unsettling the rear, and accelerating tight off the left exit.

#### B-7: Slalom Rhythm & Transient Agility
* **Car**: Lotus Elise SC (`lotus_elise_sc`) | RWD (Mid) | 217 bhp | 870 kg
* **Track / Location**: Drift Track (`drift` / `default`) — *Infield Cone Slalom*
* **Start Type**: Standing Start ($0\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:17.200`
  * 🥈 Silver: `0:18.000`
  * 🥉 Bronze: `0:19.600`
* **Objective & Lesson**: Steering cadence through 6 staggered cones. Throttle feathering in 2nd gear; using weight transfer to rotate the mid-engine chassis around each cone without scrubbing front tire grip or touching cones.

#### B-8: Blind Compression Corner Entry
* **Car**: Mazda MX-5 Miata ND (`ks_mazda_mx5_nd`) | RWD | 160 bhp | 1,000 kg
* **Track / Location**: Brands Hatch Indy (`ks_brands_hatch` / `indy`) — *Paddock Hill Bend (Turn 1)*
* **Start Type**: Rolling Start ($120\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:11.900`
  * 🥈 Silver: `0:12.500`
  * 🥉 Bronze: `0:13.600`
* **Objective & Lesson**: Downhill compression dynamics. Committing to turn-in at the blind crest, soaking the vertical compression at the bottom, and staying off the outside gravel trap.

#### B-9: All-Wheel Drive Launch & Traction Cornering
* **Car**: Audi S1 (`ks_audi_s1`) | AWD | 231 bhp | 1,315 kg
* **Track / Location**: Red Bull Ring National (`ks_red_bull_ring` / `layout_national`) — *Niki Lauda Kurve (Turn 1)*
* **Start Type**: Standing Start ($0\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:14.200`
  * 🥈 Silver: `0:14.900`
  * 🥉 Bronze: `0:16.100`
* **Objective & Lesson**: Aggressive standing AWD launch. Braking uphill deep into Turn 1, clipping the tall curb, and leveraging quattro all-wheel pull early out of the apex without inducing understeer push.

#### B-10: High-Speed Carousel Feathering
* **Car**: Toyota GT86 (`ks_toyota_gt86`) | RWD | 200 bhp | 1,230 kg
* **Track / Location**: Nürburgring Sprint (`ks_nurburgring` / `layout_sprint_a`) — *Mercedes Arena (Turns 2, 3 & 4)*
* **Start Type**: Rolling Start ($90\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:22.500`
  * 🥈 Silver: `0:23.600`
  * 🥉 Bronze: `0:25.400`
* **Objective & Lesson**: Long tightening carousel turn. Balancing the car on the edge of oversteer on low-grip factory tires; avoiding violent steering corrections that scrub time.

#### B-11: S-Bend Line Straightening
* **Car**: Ford Escort RS 1600 Mk1 (`ks_ford_escort_mk1`) | RWD | 115 bhp | 785 kg
* **Track / Location**: Circuit Zandvoort (`ks_zandvoort` / `default`) — *Gerlach to Hugenholtz (Turns 2 & 3)*
* **Start Type**: Rolling Start ($100\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:16.800`
  * 🥈 Silver: `0:17.600`
  * 🥉 Bronze: `0:19.000`
* **Objective & Lesson**: Classic lightweight live-axle rear-wheel drive. Sacrificing entry speed in Turn 2 to straighten the line and maximize rolling exit speed up the banked Hugenholtz corner.

#### B-12: Graduation: Vallelunga Club Full Lap
* **Car**: Toyota GT86 (`ks_toyota_gt86`) | RWD | 200 bhp | 1,230 kg
* **Track / Location**: Autodromo Vallelunga (`ks_vallelunga` / `club_circuit`) — *Full Circuit (1,746 m)*
* **Start Type**: Flying Lap Start ($110\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:57.900`
  * 🥈 Silver: `1:00.200`
  * 🥉 Bronze: `1:04.500`
* **Objective & Lesson**: Comprehensive National B graduation trial. Connect Curva Grande, Campagnano, Tornantino, and the final sweeping bends cleanly without exceeding track boundaries or touching barriers.

---

## 3. National A License (12 Tests)

*Intermediate vehicle dynamics: high-speed chicanes, blind off-camber drops, mid-engine weight transfer, turbo torque delivery, and powerful rear-wheel-drive sports coupes.*

**License Rewards**:
* **All Bronze**: `ks_nissan_370z` (Nissan 370Z NISMO)
* **All Gold**: `ks_porsche_718_cayman_s` (Porsche 718 Cayman S)

---

### Test Catalog: National A

#### A-1: 1000m Maximum Acceleration & High-Speed Stop
* **Car**: BMW M3 E92 Coupé (`bmw_m3_e92`) | RWD | 414 bhp | 1,605 kg
* **Track / Location**: Drag 1000m (`ks_drag` / `drag1000`)
* **Start Type**: Standing Start ($0\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:26.500`
  * 🥈 Silver: `0:27.400`
  * 🥉 Bronze: `0:29.000`
* **Objective & Lesson**: High-velocity braking from 225+ km/h. Managing the high inertia of a 1.6-tonne V8 coupe; brake smoothly to the threshold to stop cleanly inside the box without front-lock lockup.

#### A-2: The Corkscrew: Severe Elevation Drop
* **Car**: Porsche 718 Cayman S (`ks_porsche_718_cayman_s`) | RWD (Mid) | 350 bhp | 1,385 kg
* **Track / Location**: Laguna Seca (`ks_laguna_seca` / `default`) — *Turns 8 & 8A (The Corkscrew)*
* **Start Type**: Rolling Start ($130\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:15.800`
  * 🥈 Silver: `0:16.500`
  * 🥉 Bronze: `0:17.800`
* **Objective & Lesson**: Braking uphill into a completely blind crest. Sighting the oak tree marker, braking in a straight line, clipping the left curb as the track falls 5 stories, and immediately transitioning right into the bottom compression.

#### A-3: Turbo Torque Modulation on Corner Exit
* **Car**: Toyota Supra RZ MKIV (`ks_toyota_supra_mkiv`) | RWD | 326 bhp | 1,490 kg
* **Track / Location**: Autodromo di Magione (`magione` / `default`) — *Hairpins 3 & 4*
* **Start Type**: Rolling Start ($80\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:16.200`
  * 🥈 Silver: `0:17.000`
  * 🥉 Bronze: `0:18.500`
* **Objective & Lesson**: Managing sequential twin-turbo boost onset. Squeezing throttle progressively on corner exit; preventing sudden boost spikes from breaking rear traction into snap oversteer.

#### A-4: Mid-Engine Snap Oversteer Control
* **Car**: Alfa Romeo 4C (`ks_alfa_romeo_4c`) | RWD (Mid) | 240 bhp | 895 kg
* **Track / Location**: Brands Hatch Indy (`ks_brands_hatch` / `indy`) — *Graham Hill Bend (Turn 3)*
* **Start Type**: Rolling Start ($110\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:13.100`
  * 🥈 Silver: `0:13.800`
  * 🥉 Bronze: `0:14.900`
* **Objective & Lesson**: Off-camber downhill left turn. Avoiding abrupt throttle lift mid-corner which triggers instantaneous snap oversteer in a light, carbon-tub mid-engine car.

#### A-5: High-Speed Curb Bouncing Chicane
* **Car**: BMW 1M Coupé (`bmw_1m`) | RWD | 340 bhp | 1,495 kg
* **Track / Location**: Autodromo Enzo e Dino Ferrari (`imola` / `default`) — *Variante Alta (Turns 14 & 15)*
* **Start Type**: Rolling Start ($140\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:14.500`
  * 🥈 Silver: `0:15.200`
  * 🥉 Bronze: `0:16.400`
* **Objective & Lesson**: Attacking high kerbs. Straightening the steering wheel just before mounting the high curbs so the wheels absorb the shock without kicking the rear bumper sideways.

#### A-6: Group B Rally Homologation AWD Handling
* **Car**: Audi Sport quattro (`ks_audi_sport_quattro`) | AWD | 306 bhp | 1,298 kg
* **Track / Location**: Highlands Short (`ks_highlands` / `layout_short`) — *Bridges & Stone Walls Sector*
* **Start Type**: Rolling Start ($100\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:17.800`
  * 🥈 Silver: `0:18.600`
  * 🥉 Bronze: `0:20.000`
* **Objective & Lesson**: Taming a short-wheelbase front-heavy turbo AWD rally legend. Initiating turn-in early to overcome initial understeer, then powering through narrow stone-wall lined roads.

#### A-7: Downhill Hairpin Trail-Braking
* **Car**: Nissan 370Z NISMO (`ks_nissan_370z`) | RWD | 350 bhp | 1,525 kg
* **Track / Location**: Red Bull Ring GP (`ks_red_bull_ring` / `layout_gp`) — *Remus Hairpin (Turn 3)*
* **Start Type**: Rolling Start ($170\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:16.900`
  * 🥈 Silver: `0:17.700`
  * 🥉 Bronze: `0:19.000`
* **Objective & Lesson**: Steep uphill braking followed by a sharp downhill drop. Trailing brake pressure smoothly past turn-in to keep weight on the front tires and tuck the nose into the apex.

#### A-8: High-Speed Blind Crest Commitment
* **Car**: Lotus Exige 240R (`lotus_exige_240`) | RWD (Mid) | 240 bhp | 930 kg
* **Track / Location**: Circuit Zandvoort (`ks_zandvoort` / `default`) — *Scheivlak (Turn 7)*
* **Start Type**: Rolling Start ($150\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:12.400`
  * 🥈 Silver: `0:13.000`
  * 🥉 Bronze: `0:14.200`
* **Objective & Lesson**: Fast blind right-hander falling downhill. Trusting the mechanical grip of an aggressive track setup; carrying 160+ km/h through the crest without backing off.

#### A-9: High-Speed Esses Precision
* **Car**: BMW M3 E30 Step 1 (`bmw_m3_e30_s1`) | RWD | 238 bhp | 1,200 kg
* **Track / Location**: Silverstone GP (`ks_silverstone` / `gp`) — *Maggotts-Becketts Complex*
* **Start Type**: Rolling Start ($160\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:21.000`
  * 🥈 Silver: `0:22.000`
  * 🥉 Bronze: `0:23.800`
* **Objective & Lesson**: One of the fastest corner combinations in motorsport. Precision rhythm: lift slightly for Maggotts, dab brakes into Becketts, and set up a wide line into Chapel for the Hangar Straight.

#### A-10: Rotary Engine High-RPM Throttle Feathering
* **Car**: Mazda RX-7 Spirit R (`ks_mazda_rx7_spirit_r`) | RWD | 276 bhp | 1,270 kg
* **Track / Location**: Autodromo Vallelunga (`ks_vallelunga` / `classic_circuit`) — *Curva Campagnano (Turn 2)*
* **Start Type**: Rolling Start ($130\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:15.500`
  * 🥈 Silver: `0:16.300`
  * 🥉 Bronze: `0:17.500`
* **Objective & Lesson**: Long 180° sweeping turn. Keeping the twin-rotary engine singing in its high-power powerband while feathering throttle to avoid burning the rear tires.

#### A-11: Classic Rally 4WD Slide & Exit
* **Car**: Toyota Celica GT-Four ST185 (`ks_toyota_celica_st185`) | AWD | 225 bhp | 1,400 kg
* **Track / Location**: Brands Hatch Indy (`ks_brands_hatch` / `indy`) — *Surtees to Clearways (Turns 4, 5 & 6)*
* **Start Type**: Rolling Start ($110\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:18.200`
  * 🥈 Silver: `0:19.000`
  * 🥉 Bronze: `0:20.500`
* **Objective & Lesson**: Connecting off-camber linked corners. Using the 4WD system to stabilize the car across the long looping Clearways sweep and accelerating onto Brabham Straight.

#### A-12: Graduation: Brands Hatch Indy Full Lap
* **Car**: Porsche 718 Cayman S (`ks_porsche_718_cayman_s`) | RWD (Mid) | 350 bhp | 1,385 kg
* **Track / Location**: Brands Hatch Indy (`ks_brands_hatch` / `indy`) — *Full Circuit (1,929 m)*
* **Start Type**: Flying Lap Start ($130\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:52.800`
  * 🥈 Silver: `0:55.200`
  * 🥉 Bronze: `0:59.000`
* **Objective & Lesson**: Comprehensive National A graduation lap. Synthesizes blind drops, hairpin patience, off-camber trail-braking, and exit momentum across a complete sub-minute lap.

---

## 4. International B License (12 Tests)

*Advanced performance & high-speed commitment: aerodynamic downforce, supercars, slipstream overtaking, low-grip control, and high-speed chicanes.*

**License Rewards**:
* **All Bronze**: `ks_corvette_c7_stingray` (Chevrolet Corvette C7 Stingray)
* **All Gold**: `ks_porsche_911_gt3_rs` (Porsche 911 GT3 RS)

---

### Test Catalog: International B

#### IB-1: High-Speed Heavy Braking into Tamburello
* **Car**: Ferrari 458 Italia (`ferrari_458`) | RWD (Mid) | 570 bhp | 1,380 kg
* **Track / Location**: Autodromo Enzo e Dino Ferrari (`imola` / `default`) — *Tamburello Chicane (Turns 2, 3 & 4)*
* **Start Type**: Rolling Start ($240\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:15.900`
  * 🥈 Silver: `0:16.700`
  * 🥉 Bronze: `0:18.000`
* **Objective & Lesson**: High-speed deceleration from 250 km/h in a 9,000 RPM supercar. Hard initial brake hit, bleed off pressure, and flick left-right across high curbs without unsettling the rear diffuser.

#### IB-2: Rear-Engine Pendulum Dynamics & Traction
* **Car**: Porsche 911 GT3 RS 991 (`ks_porsche_911_gt3_rs`) | RWD (Rear) | 500 bhp | 1,420 kg
* **Track / Location**: Autodromo Vallelunga (`ks_vallelunga` / `extended_circuit`) — *Cimini Complex (Turns 2 & 3)*
* **Start Type**: Rolling Start ($160\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:17.800`
  * 🥈 Silver: `0:18.700`
  * 🥉 Bronze: `0:20.100`
* **Objective & Lesson**: Mastering the rear-engine layout. Deep trail-braking to pin the front tires into Cimini 1, followed by utilizing huge rear traction over the rear axle to launch through Cimini 2.

#### IB-3: Downforce Commitment: Pouhon Double-Apex
* **Car**: Lotus 2-Eleven (`lotus_2_eleven`) | RWD (Mid) | 255 bhp | 670 kg
* **Track / Location**: Circuit de Spa-Francorchamps (`spa` / `default`) — *Pouhon (Turns 10 & 11)*
* **Start Type**: Rolling Start ($170\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:19.400`
  * 🥈 Silver: `0:20.300`
  * 🥉 Bronze: `0:22.000`
* **Objective & Lesson**: Legendary high-speed downhill double-left. In a lightweight aero car, tap the brake lightly, tuck into the first apex at 170 km/h, let the car float to mid-track, and pull tight for the second apex.

#### IB-4: Big Displacement V8 Torque Modulation
* **Car**: Chevrolet Corvette C7 Stingray (`ks_corvette_c7_stingray`) | RWD | 460 bhp | 1,500 kg
* **Track / Location**: Laguna Seca (`ks_laguna_seca` / `default`) — *Andretti Hairpin (Turn 2)*
* **Start Type**: Rolling Start ($150\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:16.800`
  * 🥈 Silver: `0:17.600`
  * 🥉 Bronze: `0:19.000`
* **Objective & Lesson**: Tight double-apex hairpin. Managing 630 Nm of torque in 2nd gear; waiting until the car is pointed straight before pinning the throttle to prevent power oversteer.

#### IB-5: Active Aerodynamics at 230 km/h
* **Car**: Lamborghini Huracán Performante (`ks_lamborghini_huracan_performante`) | AWD (Mid) | 640 bhp | 1,382 kg
* **Track / Location**: Circuit de Barcelona-Catalunya (`ks_barcelona` / `layout_gp`) — *Turn 3 (Curvone)*
* **Start Type**: Rolling Start ($180\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:14.200`
  * 🥈 Silver: `0:14.900`
  * 🥉 Bronze: `0:16.000`
* **Objective & Lesson**: Long uphill high-speed sweeper. Trusting the Aerodinamica Lamborghini Attiva (ALA) vectoring downforce; pinning the throttle at 220+ km/h without backing off.

#### IB-6: High-Speed Chicane Precision: Ascari
* **Car**: BMW M3 E92 Step 1 (`bmw_m3_e92_s1`) | RWD | 414 bhp | 1,605 kg
* **Track / Location**: Autodromo Nazionale Monza (`monza` / `default`) — *Variante Ascari (Turns 8, 9 & 10)*
* **Start Type**: Rolling Start ($220\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:18.500`
  * 🥈 Silver: `0:19.400`
  * 🥉 Bronze: `0:20.800`
* **Objective & Lesson**: High-speed entrance into left-right-left transition. Hard braking into Turn 8, clipping the right curb at Turn 9, and carrying full acceleration flat-out through Turn 10 towards the back straight.

#### IB-7: Heavyweight Digital AWD Traction
* **Car**: Nissan GT-R R35 NISMO (`ks_nissan_gtr`) | AWD | 600 bhp | 1,720 kg
* **Track / Location**: Nürburgring GP (`ks_nurburgring` / `layout_gp_a`) — *Kumho Kurve & Chicane (Turns 12, 13 & 14)*
* **Start Type**: Rolling Start ($160\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:19.100`
  * 🥈 Silver: `0:20.000`
  * 🥉 Bronze: `0:21.500`
* **Objective & Lesson**: Managing 1.7 tonnes at race pace. Braking in a straight line, letting the electronic ATTESA differential sort traction, and rocketing out of the final chicane.

#### IB-8: Blind Crest Downhill Esses: Casanova-Savelli
* **Car**: Alfa Romeo Giulia Quadrifoglio (`ks_alfa_romeo_giulia_quadrifoglio`) | RWD | 505 bhp | 1,580 kg
* **Track / Location**: Autodromo del Mugello (`mugello` / `default`) — *Casanova-Savelli (Turns 6 & 7)*
* **Start Type**: Rolling Start ($170\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:15.600`
  * 🥈 Silver: `0:16.400`
  * 🥉 Bronze: `0:17.800`
* **Objective & Lesson**: Severe downhill S-curve. Unloading the suspension over the Casanova crest, quick dab of brakes, and pitching the car left into Savelli as the road drops away.

#### IB-9: Slipstream Drafting & Clean Overtake
* **Car**: Mazda MX-5 Cup (`ks_mazda_mx5_cup`) | RWD | 160 bhp | 950 kg
* **Opponents**: 2x AI Mazda MX-5 Cup
* **Track / Location**: Red Bull Ring GP (`ks_red_bull_ring` / `layout_gp`) — *Turn 1 to Turn 3 Straight*
* **Start Type**: Rolling Start ($120\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:24.000`
  * 🥈 Silver: `0:25.200`
  * 🥉 Bronze: `0:27.000`
* **Objective & Lesson**: Drafting behind two spec race cars. Tucking into the slipstream to gain 15 km/h, pulling out to make a clean, non-contact pass into the heavy braking zone of Turn 3 before crossing the finish.

#### IB-10: High-Speed Parabolica Exit Momentum
* **Car**: Ferrari 488 GTB (`ks_ferrari_488_gtb`) | RWD (Mid) | 661 bhp | 1,370 kg
* **Track / Location**: Autodromo Nazionale Monza (`monza` / `default`) — *Curva Parabolica (Turn 11)*
* **Start Type**: Rolling Start ($180\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:17.200`
  * 🥈 Silver: `0:18.000`
  * 🥉 Bronze: `0:19.400`
* **Objective & Lesson**: Decreasing-radius high-speed sweeper opening onto the main straight. Trail-braking deep, hugging the inside line, and opening the steering wheel early to reach 260+ km/h across the finish.

#### IB-11: Historic High-Speed Drifting: Stowe & Club
* **Car**: Shelby Cobra 427 S/C (`shelby_cobra_427sc`) | RWD | 425 bhp | 1,043 kg
* **Track / Location**: Silverstone 1967 (`ks_silverstone1967` / `default`) — *Stowe to Club Complex*
* **Start Type**: Rolling Start ($150\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:23.500`
  * 🥈 Silver: `0:24.600`
  * 🥉 Bronze: `0:26.500`
* **Objective & Lesson**: 1960s cross-ply tires and monstrous V8 power. Controlling sustained 4-wheel slip angle through high-speed bends without barriers; feathering throttle to avoid spinning into open fields.

#### IB-12: Graduation: Red Bull Ring GP Full Lap
* **Car**: Porsche 911 GT3 RS 991 (`ks_porsche_911_gt3_rs`) | RWD (Rear) | 500 bhp | 1,420 kg
* **Track / Location**: Red Bull Ring GP (`ks_red_bull_ring` / `layout_gp`) — *Full Circuit (4,326 m)*
* **Start Type**: Flying Lap Start ($160\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `1:36.500`
  * 🥈 Silver: `1:40.000`
  * 🥉 Bronze: `1:46.000`
* **Objective & Lesson**: Complete International B graduation test. Full 4.3 km lap linking uphill heavy braking, off-camber drops, and fast aerodynamic 4th gear sweeps with zero track limit infringements.

---

## 5. International A License (12 Tests)

*Professional motorsport racecraft: GT3, GT4, and classic DTM race cars. Full slick tires, racing ABS/TC, high-downforce aero packages, multi-class clean overtakes, and curb discipline.*

**License Rewards**:
* **All Bronze**: `ks_porsche_cayman_gt4_clubsport` (Porsche Cayman GT4 Clubsport)
* **All Gold**: `ks_ferrari_488_gt3` (Ferrari 488 GT3)

---

### Test Catalog: International A

#### IA-1: The Benchmark: Eau Rouge & Raidillon Flat-Out
* **Car**: Ferrari 488 GT3 (`ks_ferrari_488_gt3`) | RWD (Mid) | 550 bhp | 1,260 kg
* **Track / Location**: Circuit de Spa-Francorchamps (`spa` / `default`) — *Turns 2, 3, 4 & 5 (Eau Rouge / Raidillon)*
* **Start Type**: Rolling Start ($180\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:14.200`
  * 🥈 Silver: `0:14.900`
  * 🥉 Bronze: `0:16.000`
* **Objective & Lesson**: Motorsport's most famous complex. Compressing at the bottom of Eau Rouge, flicking right up the blind 18% hill, clipping the left curb of Raidillon, and cresting onto Kemmel Straight at 240+ km/h without lifting or lifting only a fraction.

#### IA-2: GT4 Trail-Braking & Weight Conservation
* **Car**: Porsche Cayman GT4 Clubsport (`ks_porsche_cayman_gt4_clubsport`) | RWD (Mid) | 385 bhp | 1,300 kg
* **Track / Location**: Brands Hatch GP (`ks_brands_hatch` / `gp`) — *Westfield to Dingle Dell (Turns 6, 7 & 8)*
* **Start Type**: Rolling Start ($140\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:18.400`
  * 🥈 Silver: `0:19.300`
  * 🥉 Bronze: `0:20.800`
* **Objective & Lesson**: Fast woodland section of Brands GP. Hard trail braking into Westfield, carrying momentum through the dip, and clipping the blind apex of Dingle Dell with race slicks.

#### IA-3: Extreme Downforce Cornering: Arrabbiata 1 & 2
* **Car**: Audi R8 LMS 2016 (`ks_audi_r8_lms_2016`) | RWD (Mid) | 500 bhp | 1,225 kg
* **Track / Location**: Autodromo del Mugello (`mugello` / `default`) — *Arrabbiata 1 & 2 (Turns 8 & 9)*
* **Start Type**: Rolling Start ($170\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:17.500`
  * 🥈 Silver: `0:18.300`
  * 🥉 Bronze: `0:19.600`
* **Objective & Lesson**: Back-to-back uphill right-hand sweepers pulling over 2.5G. Squeezing full downforce out of the GT3 rear wing; holding a tight line through Arrabbiata 1 and maintaining flat throttle through the crest of Arrabbiata 2.

#### IA-4: Classic DTM Aggressive Curb Hopping
* **Car**: Alfa Romeo 155 V6 TI DTM (`ks_alfa_romeo_155_v6_ti`) | AWD | 420 bhp | 1,040 kg
* **Track / Location**: Autodromo Enzo e Dino Ferrari (`imola` / `default`) — *Villeneuve Chicane (Turns 5 & 6)*
* **Start Type**: Rolling Start ($180\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:13.900`
  * 🥈 Silver: `0:14.600`
  * 🥉 Bronze: `0:15.800`
* **Objective & Lesson**: 12,000 RPM high-downforce AWD touring car. Aggressively launching over the high yellow curb stones; keeping the throttle pinned to let the AWD pull the car straight upon landing.

#### IA-5: Front-Mid GT3 Platform Stability
* **Car**: Mercedes-AMG GT3 (`ks_mercedes_amg_gt3`) | RWD (Front-Mid) | 500 bhp | 1,285 kg
* **Track / Location**: Circuit de Barcelona-Catalunya (`ks_barcelona` / `layout_gp`) — *Turns 1, 2 & 3 (Elf & Renault)*
* **Start Type**: Rolling Start ($220\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:22.000`
  * 🥈 Silver: `0:23.000`
  * 🥉 Bronze: `0:24.800`
* **Objective & Lesson**: Heavy braking from 240 km/h into a tight uphill flick (Turn 1/2) followed immediately by the long Turn 3 sweeper. Managing front-tire heat and maintaining aero balance.

#### IA-6: Bus Stop Chicane: Braking from 270 km/h
* **Car**: McLaren 650S GT3 (`ks_mclaren_650s_gt3`) | RWD (Mid) | 500 bhp | 1,240 kg
* **Track / Location**: Circuit de Spa-Francorchamps (`spa` / `default`) — *Bus Stop Chicane (Turns 19 & 20)*
* **Start Type**: Rolling Start ($250\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:16.800`
  * 🥈 Silver: `0:17.600`
  * 🥉 Bronze: `0:19.000`
* **Objective & Lesson**: Braking from Blanchimont into the tightest chicane on the circuit. Setting racing brake bias, stopping from 260 km/h down to 65 km/h, and squaring off the right-left exit onto the start straight.

#### IA-7: Rear-Engine GT3 Pivot & Curb Launch
* **Car**: Porsche 911 GT3 R 2016 (`ks_porsche_911_gt3_r_2016`) | RWD (Rear) | 500 bhp | 1,220 kg
* **Track / Location**: Nürburgring GP (`ks_nurburgring` / `layout_gp_a`) — *Castrol-S Chicane (Turns 1 & 2)*
* **Start Type**: Rolling Start ($170\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:15.200`
  * 🥈 Silver: `0:16.000`
  * 🥉 Bronze: `0:17.400`
* **Objective & Lesson**: Downhill braking into tight chicane. Trail-braking to rotate the rear-engine chassis quickly, bouncing over the left curb, and hammering the throttle over the right exit curb.

#### IA-8: GTE Aerodynamic Diffuser Suction
* **Car**: Porsche 911 RSR 2017 (`ks_porsche_911_rsr_2017`) | RWD (Mid) | 510 bhp | 1,243 kg
* **Track / Location**: Silverstone GP (`ks_silverstone` / `gp`) — *Copse Corner (Turn 9)*
* **Start Type**: Rolling Start ($220\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:10.900`
  * 🥈 Silver: `0:11.500`
  * 🥉 Bronze: `0:12.600`
* **Objective & Lesson**: 230+ km/h blind right-hander. Mid-engine inverted GTE diffuser suction allows carrying staggering apex speed; dab brake, turn in decisively, and ride the exit rumble strip.

#### IA-9: Analog 1960s Prototype Mastery
* **Car**: Ford GT40 Mk.I (`ks_ford_gt40`) | RWD (Mid) | 385 bhp | 998 kg
* **Track / Location**: Monza 1966 Road (`ks_monza66` / `road`) — *Curva Grande & Lesmo 1 & 2*
* **Start Type**: Rolling Start ($200\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:28.500`
  * 🥈 Silver: `0:30.000`
  * 🥉 Bronze: `0:32.500`
* **Objective & Lesson**: Vintage cross-ply racing slicks, heavy clutch, zero assists. Navigating high-speed sweeping curves with precise steering angles and countersteering micro-corrections.

#### IA-10: Multi-Car GT3 Traffic Overtake
* **Car**: Ferrari 488 GT3 (`ks_ferrari_488_gt3`) | RWD (Mid) | 550 bhp | 1,260 kg
* **Opponents**: 3x AI GT4 Cars (Cayman GT4 & Maserati MC GT4)
* **Track / Location**: Nürburgring Sprint (`ks_nurburgring` / `layout_sprint_a`) — *Full Sprint Sector*
* **Start Type**: Rolling Start ($140\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:42.500`
  * 🥈 Silver: `0:44.800`
  * 🥉 Bronze: `0:48.000`
* **Objective & Lesson**: Clean multi-class passing challenge. Overtake three slower GT4 cars cleanly without any body contact or off-track excursions before crossing the sector line.

#### IA-11: Classic DTM Heel-and-Toe Dogfight
* **Car**: Mercedes-Benz 190E Evo II DTM (`ks_mercedes_190_evo2`) | RWD | 370 bhp | 980 kg
* **Track / Location**: Autodromo Vallelunga (`ks_vallelunga` / `extended_circuit`) — *Trincea to Semaforo (Turns 5 to 8)*
* **Start Type**: Rolling Start ($150\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `0:22.800`
  * 🥈 Silver: `0:24.000`
  * 🥉 Bronze: `0:26.000`
* **Objective & Lesson**: Fast, narrow sequence of sweeping turns. Rev-matching downshifts into Semaforo hairpin; maximizing mechanical grip from an unassisted analog race chassis.

#### IA-12: Graduation: Circuit de Spa-Francorchamps Sector Trial
* **Car**: Ferrari 488 GT3 (`ks_ferrari_488_gt3`) | RWD (Mid) | 550 bhp | 1,260 kg
* **Track / Location**: Circuit de Spa-Francorchamps (`spa` / `default`) — *Sector 2 (Les Combes to Stavelot)*
* **Start Type**: Rolling Start ($190\text{ km/h}$)
* **Target Times**: 
  * 🥇 Gold: `1:04.500`
  * 🥈 Silver: `1:07.500`
  * 🥉 Bronze: `1:12.000`
* **Objective & Lesson**: Comprehensive International A graduation sector. Navigates Les Combes chicane, Bruxelles downhill carousel, the left flick, flat Pouhon, and the fast right sweep into Stavelot without a single tire exceeding track limits.

---

## 6. Super License (10 Full-Lap Tests)

*The ultimate test of speed, discipline, and endurance: full timed laps with zero margin for error across the world's most demanding circuits in Hypercars, Group C legends, LMP1 prototypes, and Formula 1 machinery.*

**License Rewards**:
* **All Bronze**: `pagani_zonda_r` (Pagani Zonda R)
* **All Gold**: `ks_ferrari_f2004` (Ferrari F2004 Formula 1)

---

### Test Catalog: Super License

#### S-1: Supercar Hot Lap: Laguna Seca
* **Car**: Ferrari LaFerrari (`ferrari_laferrari`) | RWD (Mid) | 963 bhp | 1,255 kg
* **Track**: WeatherTech Raceway Laguna Seca (`ks_laguna_seca` / `default`) — *3,602 m*
* **Target Times**: 
  * 🥇 Gold: `1:20.500`
  * 🥈 Silver: `1:24.000`
  * 🥉 Bronze: `1:30.000`
* **Objective**: Full unassisted hot lap in a 963 bhp hybrid hypercar. Managing explosive electric torque out of the Andretti hairpin, high-g commitment through Turn 6, and navigating the Corkscrew drop cleanly.

#### S-2: British Heritage Time Attack: Brands Hatch GP
* **Car**: McLaren P1 (`ks_mclaren_p1`) | RWD (Mid) | 916 bhp | 1,395 kg
* **Track**: Brands Hatch GP (`ks_brands_hatch` / `gp`) — *3,908 m*
* **Target Times**: 
  * 🥇 Gold: `1:24.200`
  * 🥈 Silver: `1:28.000`
  * 🥉 Bronze: `1:34.000`
* **Objective**: Full lap around the narrow, barrier-lined Brands Hatch Grand Prix circuit. Active aero and DRS deployment; high concentration through fast off-camber woodland curves.

#### S-3: High-Downforce Aerodynamic Flow: Mugello
* **Car**: Pagani Zonda R (`pagani_zonda_r`) | RWD (Mid) | 750 bhp | 1,070 kg
* **Track**: Autodromo del Mugello (`mugello` / `default`) — *5,245 m*
* **Target Times**: 
  * 🥇 Gold: `1:39.800`
  * 🥈 Silver: `1:44.000`
  * 🥉 Bronze: `1:51.000`
* **Objective**: Full lap in a naturally aspirated V12 track special. Zero driving assists; connecting Casanova-Savelli, Arrabbiata 1 & 2, and Correntaio into one seamless high-g rhythm.

#### S-4: High-Velocity Temple of Speed: Monza GP
* **Car**: Sauber-Mercedes C9 (`ks_mercedes_c9`) | RWD (Mid) | 720 bhp | 900 kg
* **Track**: Autodromo Nazionale Monza (`monza` / `default`) — *5,793 m*
* **Target Times**: 
  * 🥇 Gold: `1:34.500`
  * 🥈 Silver: `1:39.000`
  * 🥉 Bronze: `1:46.000`
* **Objective**: 1989 Group C Le Mans winner around Monza. Exceeding 340 km/h on the straights, managing heavy turbo spool, and executing precise heavy braking into Prima Variante and Ascari.

#### S-5: The 4-Rotor Symphony: Silverstone GP
* **Car**: Mazda 787B (`ks_mazda_787b`) | RWD (Mid) | 700 bhp | 830 kg
* **Track**: Silverstone GP (`ks_silverstone` / `gp`) — *5,901 m*
* **Target Times**: 
  * 🥇 Gold: `1:47.800`
  * 🥈 Silver: `1:52.500`
  * 🥉 Bronze: `2:00.000`
* **Objective**: Full lap in the 1991 Le Mans-winning rotary prototype. Heel-toe downshifting without synchros; pinning the throttle through Copse and Maggotts-Becketts-Chapel.

#### S-6: Undulating Perfection: Imola GP
* **Car**: Porsche 962c Short Tail (`ks_porsche_962c_shorttail`) | RWD (Mid) | 750 bhp | 850 kg
* **Track**: Autodromo Enzo e Dino Ferrari (`imola` / `default`) — *4,909 m*
* **Target Times**: 
  * 🥇 Gold: `1:35.200`
  * 🥈 Silver: `1:39.500`
  * 🥉 Bronze: `1:46.000`
* **Objective**: Ground-effect underbody tunnels around Imola. High aerodynamic suction keeps the car glued to the track through Piratella and Acque Minerali; zero curb slamming.

#### S-7: Modern Hybrid Prototype Mastery: Spa-Francorchamps
* **Car**: Porsche 919 Hybrid 2016 (`ks_porsche_919_hybrid_2016`) | AWD (Mid) | 900+ bhp | 875 kg
* **Track**: Circuit de Spa-Francorchamps (`spa` / `default`) — *7,004 m*
* **Target Times**: 
  * 🥇 Gold: `1:54.000`
  * 🥈 Silver: `1:59.000`
  * 🥉 Bronze: `2:07.000`
* **Objective**: 8-Megajoule LMP1 hybrid endurance monster. Electric front-wheel drive launch out of La Source, flat-out through Eau Rouge, and energy regeneration under braking into the Bus Stop.

#### S-8: 1,000 Horsepower Hybrid Attack: Red Bull Ring
* **Car**: Toyota TS040 Hybrid (`ks_toyota_ts040`) | AWD (Mid) | 1,000 bhp | 870 kg
* **Track**: Red Bull Ring GP (`ks_red_bull_ring` / `layout_gp`) — *4,326 m*
* **Target Times**: 
  * 🥇 Gold: `1:18.500`
  * 🥈 Silver: `1:22.000`
  * 🥉 Bronze: `1:28.000`
* **Objective**: Complete hot lap in Toyota's WEC World Championship prototype. Utilizing instant capacitor boost down the uphill straights and carrying massive speed through the final two sweepers.

#### S-9: Formula 1 V10 Apex Velocity: Barcelona GP
* **Car**: Ferrari F2004 (`ks_ferrari_f2004`) | RWD | 950 bhp | 605 kg
* **Track**: Circuit de Barcelona-Catalunya (`ks_barcelona` / `layout_gp`) — *4,655 m*
* **Target Times**: 
  * 🥇 Gold: `1:14.200`
  * 🥈 Silver: `1:17.500`
  * 🥉 Bronze: `1:23.000`
* **Objective**: The benchmark Formula 1 car of all time (V10 19,000 RPM). Generating over 4.5G in lateral cornering and pulling $100\text{ m}$ braking distances from 310 km/h. Zero room for hesitation.

#### S-10: The Ultimate Trial: Nürburgring Nordschleife Hot Lap
* **Car**: Mercedes-Benz 190E Evo II DTM (`ks_mercedes_190_evo2`) | RWD | 370 bhp | 980 kg
* **Track**: Nürburgring Nordschleife (`ks_nordschleife` / `nordschleife`) — *20,832 m*
* **Target Times**: 
  * 🥇 Gold: `7:08.500`
  * 🥈 Silver: `7:25.000`
  * 🥉 Bronze: `7:55.000`
* **Objective**: Direct homage to Gran Turismo 4's legendary S-16 test. A complete, unassisted hot lap of the Green Hell (154 turns, 20.8 km) in an authentic DTM touring car. A single barrier touch, spin, or 4-wheels-off infraction triggers an instant disqualification.

---

## 7. Summary & Implementation Mapping

```
+---------------------------------------------------------------------------------------------------+
| TIER          | TESTS | THEMATIC FOCUS                                | PRIZE (BRONZE)  | PRIZE (GOLD)   |
+---------------------------------------------------------------------------------------------------+
| National B    |  12   | Kinematics, Braking, Out-In-Out, Low-Power FR | MiTo QV         | Toyota GT86    |
| National A    |  12   | Complex Chicanes, Elevation, Turbo, Mid-Engine| Nissan 370Z     | Cayman S       |
| Internat. B   |  12   | Supercars, Downforce, Overtaking, Low-Grip    | Corvette C7     | 911 GT3 RS     |
| Internat. A   |  12   | GT3 / GT4 / DTM, Slick Tires, Multi-Class     | Cayman GT4 Club | 488 GT3        |
| Super License |  10   | Full Circuit Time Trials, LMP1 & Formula 1    | Pagani Zonda R  | Ferrari F2004  |
+---------------------------------------------------------------------------------------------------+
| TOTAL TESTS   |  58   | 100% Kunos Official Content (Zero external mods required)                        |
+---------------------------------------------------------------------------------------------------+
```
