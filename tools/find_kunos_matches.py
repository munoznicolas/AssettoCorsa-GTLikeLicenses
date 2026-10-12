import json
import re

with open('docs/Gran_Turismo_License_Tests.json', 'r', encoding='utf-8', errors='ignore') as f:
    gt_tests = json.load(f)

with open('docs/03_kunos_official_resources_catalog.md', 'r', encoding='utf-8') as f:
    catalog_lines = f.readlines()

# Extract tracks
kunos_tracks = [
    ('Brands Hatch', ['brands hatch'], 'ks_brands_hatch'),
    ('Silverstone', ['silverstone'], 'ks_silverstone'),
    ('Red Bull Ring', ['red bull ring'], 'ks_red_bull_ring'),
    ('Nürburgring Nordschleife', ['nordschleife'], 'ks_nordschleife'),
    ('Nürburgring GP / Sprint', ['nürburgring', 'nurburgring'], 'ks_nurburgring'),
    ('Circuit de Barcelona-Catalunya', ['barcelona', 'catalunya'], 'ks_barcelona'),
    ('Autodromo Nazionale Monza', ['monza'], 'monza'),
    ('Circuit de Spa-Francorchamps', ['spa'], 'spa'),
    ('WeatherTech Raceway Laguna Seca', ['laguna seca'], 'ks_laguna_seca'),
]

# Analyze tracks
print("="*80)
print("1. KUNOS TRACKS APPEARING IN GRAN TURISMO LICENSE TESTS")
print("="*80)

track_results = {}
for t in gt_tests:
    tr = t.get('track', '')
    tr_low = tr.lower()
    if 'dragon' in tr_low: # Skip Dragon Trail (fictional)
        continue
    matched = None
    if 'nordschleife' in tr_low:
        matched = ('Nürburgring Nordschleife', 'ks_nordschleife')
    else:
        for tname, patterns, trk_id in kunos_tracks:
            if tname == 'Nürburgring Nordschleife': continue
            if any(p in tr_low for p in patterns):
                matched = (tname, trk_id)
                break
    if matched:
        if matched not in track_results:
            track_results[matched] = []
        track_results[matched].append(t)

total_track_tests = sum(len(v) for v in track_results.values())
print(f"Total matching real-world tracks: {len(track_results)} tracks featured in {total_track_tests} GT tests\n")

for (tname, trk_id), tests in sorted(track_results.items()):
    by_game = {}
    for x in tests:
        by_game.setdefault(x['game'], []).append(x['code'])
    print(f"* **{tname}** (`{trk_id}`) - {len(tests)} tests:")
    for g, codes in sorted(by_game.items()):
        print(f"    - **{g}** ({len(codes)}): {', '.join(codes)}")

print("\n" + "="*80)
print("2. KUNOS CARS APPEARING IN GRAN TURISMO LICENSE TESTS")
print("="*80)

gt_car_to_tests = {}
for t in gt_tests:
    c = t.get('car', '').strip()
    gt_car_to_tests.setdefault(c, []).append((t['game'], t['code'], t.get('track', '')))

car_matches = []

for gt_car, tests in sorted(gt_car_to_tests.items()):
    gc = gt_car.lower()
    match_info = None
    
    # Abarth
    if 'abarth 500' in gc:
        match_info = ('Abarth 500 EsseEsse', 'abarth500', 'Exact model family (Kunos EsseEsse & S1)')
    
    # Alfa Romeo
    elif 'giulia sprint gta 1600' in gc or 'gta 1600' in gc:
        match_info = ('Alfa Romeo GTA', 'ks_alfa_romeo_gta', 'Exact model (1965 GTA 1600)')
    elif 'alfa romeo 155' in gc and ('touring car' in gc or 'v6' in gc or 'dtm' in gc):
        match_info = ('Alfa Romeo 155 V6 TI DTM', 'ks_alfa_romeo_155_v6_ti', 'Exact touring car legend')
    elif 'alfa romeo 4c' in gc:
        match_info = ('Alfa Romeo 4C', 'ks_alfa_romeo_4c', 'Exact mid-engine sports car')
    elif 'mito' in gc:
        match_info = ('Alfa Romeo MiTo Quadrifoglio Verde', 'ks_alfa_romeo_mito_qv', 'Direct MiTo model counterpart')
    
    # Audi
    elif 'audi r8 5.2' in gc or 'audi r8 race car' in gc or 'audi r8 4.2' in gc:
        match_info = ('Audi R8 V10 Plus (2016) / R8 LMS', 'ks_audi_r8_plus / ks_audi_r8_lms', 'R8 generation / GT3 counterpart')
    elif 'audi sport quattro' in gc:
        match_info = ('Audi Sport quattro', 'ks_audi_sport_quattro', 'Exact model counterpart')
    
    # BMW
    elif 'bmw m3 sport evolution' in gc or 'bmw m3 \'89' in gc:
        match_info = ('BMW M3 E30', 'bmw_m3_e30', 'Exact E30 generation')
    elif 'bmw m3 coup' in gc and '07' in gc:
        match_info = ('BMW M3 E92 Coupé', 'bmw_m3_e92', 'Exact E92 V8 generation')
    elif 'bmw z4' in gc and ('03' in gc or '08' in gc):
        match_info = ('BMW Z4 E89 sDrive 35is', 'bmw_z4', 'BMW Z4 platform counterpart')
    
    # Chevrolet
    elif 'corvette stingray (c7)' in gc or 'corvette c7' in gc:
        match_info = ('Chevrolet Corvette C7 Stingray', 'ks_corvette_c7_stingray', 'Exact C7 generation')
    
    # Ferrari
    elif 'ferrari f40' in gc:
        match_info = ('Ferrari F40', 'ferrari_f40', 'Exact iconic supercar')
    elif 'ferrari 458 italia' in gc:
        match_info = ('Ferrari 458 Italia', 'ferrari_458', 'Exact model')
    elif 'ferrari 330 p4' in gc:
        match_info = ('Ferrari 330 P4', 'ks_ferrari_330_p4', 'Exact 1967 endurance prototype')
    elif 'ferrari gto \'84' in gc or 'gto \'84' in gc:
        match_info = ('Ferrari 288 GTO', 'ks_ferrari_288_gto', 'Exact model (1984 288 GTO)')
    
    # Ford
    elif 'ford gt40' in gc and ('66' in gc or '69' in gc):
        match_info = ('Ford GT40 Mk.I', 'ks_ford_gt40', 'Exact Mk.I Le Mans legend')
    elif 'mustang gt \'15' in gc or 'mustang \'15' in gc:
        match_info = ('Ford Mustang 5.0 V8 (2015)', 'ks_ford_mustang_2015', 'Exact S550 Mustang V8')
    
    # KTM
    elif 'ktm x-bow' in gc:
        match_info = ('KTM X-Bow R', 'ktm_x_bow_r', 'Exact trackday weapon')
    
    # Lamborghini
    elif 'aventador lp 750-4 superveloce' in gc or 'aventador lp700-4' in gc:
        match_info = ('Lamborghini Aventador SV', 'ks_lamborghini_aventador_sv', 'Exact Aventador SV / flagship')
    elif 'countach lp400' in gc or 'countach 25th' in gc:
        match_info = ('Lamborghini Countach 5000 QV', 'ks_lamborghini_countach', 'Countach flagship classic')
    elif 'miura p400' in gc:
        match_info = ('Lamborghini Miura P400 SV', 'ks_lamborghini_miura_sv', 'Exact Miura supercar')
    elif 'gallardo lp 560-4' in gc:
        match_info = ('Lamborghini Gallardo SL', 'ks_lamborghini_gallardo_sl', 'Gallardo platform counterpart')
    
    # Lotus
    elif 'lotus elise' in gc:
        match_info = ('Lotus Elise SC', 'lotus_elise_sc', 'Lightweight Elise platform counterpart')
    elif 'lotus evora' in gc:
        match_info = ('Lotus Evora S', 'lotus_evora_s', 'Evora sports coupe counterpart')
    
    # Mazda
    elif any(x in gc for x in ['eunos roadster', 'mazda roadster']):
        if any(yr in gc for yr in ['89', '91', '93']):
            match_info = ('Mazda MX-5 Miata (NA 1991)', 'ks_mazda_miata', 'Exact NA generation')
        elif 'nd' in gc or '15' in gc:
            match_info = ('Mazda MX-5 Miata (ND 2015)', 'ks_mazda_mx5_nd', 'Exact ND generation')
        else:
            match_info = ('Mazda MX-5 Miata (NA 1991)', 'ks_mazda_miata', 'MX-5 / Roadster generation counterpart')
    elif 'rx-7' in gc and ('fd' in gc or 'spirit r' in gc or 'type r' in gc):
        match_info = ('Mazda RX-7 Spirit R (FD)', 'ks_mazda_rx7_spirit_r', 'Exact FD3S twin-turbo platform')
    elif '787b' in gc:
        match_info = ('Mazda 787B', 'ks_mazda_787b', 'Exact Group C rotary Le Mans winner')
    
    # McLaren
    elif 'mp4-12c' in gc:
        match_info = ('McLaren 12C', 'mclaren_mp412c', 'Exact twin-turbo V8 supercar')
    
    # Mercedes-Benz / Sauber
    elif '190 e 2.5 - 16 evolution ii' in gc:
        match_info = ('Mercedes-Benz 190E Evo II DTM', 'ks_mercedes_190_evo2', 'Exact Evo II touring car counterpart')
    elif 'sls amg' in gc and 'gt3' not in gc:
        match_info = ('Mercedes-Benz SLS AMG', 'mercedes_sls', 'Exact gullwing supercar')
    elif 'sauber mercedes c9' in gc or 'sauber-mercedes c9' in gc:
        match_info = ('Sauber-Mercedes C9', 'ks_mercedes_c9', 'Exact Group C Silver Arrow')
    
    # Nissan
    elif 'fairlady z (z34)' in gc or '370z' in gc:
        match_info = ('Nissan 370Z NISMO', 'ks_nissan_370z', 'Exact Z34 3.7L V6 coupe')
    elif 'skyline gt-r' in gc and ('r34' in gc or 'v-spec' in gc or 'v - spec' in gc or 'bnr34' in gc):
        match_info = ('Nissan Skyline GT-R R34 V-Spec', 'ks_nissan_skyline_r34', 'Exact R34 RB26DETT AWD')
    elif 'nissan gt-r' in gc and ('black edition' in gc or 'specv' in gc or 'gt500' in gc):
        match_info = ('Nissan GT-R R35 NISMO', 'ks_nissan_gtr', 'Exact R35 VR38DETT AWD')
    
    # Pagani
    elif 'zonda r' in gc:
        match_info = ('Pagani Zonda R', 'pagani_zonda_r', 'Exact extreme track hypercar')
    
    # Porsche
    elif 'porsche 917k' in gc:
        match_info = ('Porsche 917 K', 'ks_porsche_917_k', 'Exact classic Le Mans flat-12 prototype')
    elif '962 c' in gc or '962c' in gc:
        match_info = ('Porsche 962c', 'ks_porsche_962c_shorttail', 'Exact Group C prototype')
    elif '911 gt1' in gc:
        match_info = ('Porsche 911 GT1-98', 'ks_porsche_911_gt1', 'Porsche 911 GT1 homologation / race')
    elif 'cayman gt4' in gc:
        match_info = ('Porsche Cayman GT4 (Road)', 'ks_porsche_cayman_gt4', 'Exact 981 Cayman GT4')
    
    # RUF
    elif 'ruf ctr' in gc or 'yellow bird' in gc:
        match_info = ('RUF CTR Yellowbird', 'ruf_yellowbird', 'Exact 469 bhp twin-turbo legend')
    
    # Toyota
    elif 'sprinter trueno' in gc and 'ae86' in gc:
        match_info = ('Toyota AE86 Sprinter Trueno', 'ks_toyota_ae86', 'Exact 4A-GE FR coupe')
    elif 'toyota 86 gt' in gc or 'ft-86' in gc:
        match_info = ('Toyota GT86', 'ks_toyota_gt86', 'Exact boxer FR sports car')
    elif 'celica gt-four' in gc and 'st185' in gc:
        match_info = ('Toyota Celica GT-Four ST185', 'ks_toyota_celica_st185', 'Exact rally homologation AWD')
    elif 'supra rz' in gc or ('supra' in gc and any(y in gc for y in ['96', '97', 'toms', 'gt500'])):
        match_info = ('Toyota Supra RZ (MKIV)', 'ks_toyota_supra_mkiv', 'Exact 2JZ-GTE MKIV turbo coupe')

    if match_info:
        car_matches.append({
            'gt_car': gt_car,
            'kunos_name': match_info[0],
            'kunos_id': match_info[1],
            'notes': match_info[2],
            'tests': tests
        })

# Aggregate by Kunos vehicle
kunos_to_matches = {}
for m in car_matches:
    kid = m['kunos_id']
    if kid not in kunos_to_matches:
        kunos_to_matches[kid] = {
            'name': m['kunos_name'],
            'notes': m['notes'],
            'gt_variants': [],
            'all_tests': []
        }
    kunos_to_matches[kid]['gt_variants'].append(m['gt_car'])
    kunos_to_matches[kid]['all_tests'].extend(m['tests'])

print(f"Total unique Kunos vehicle models represented: {len(kunos_to_matches)} models across {len(car_matches)} GT variants\n")

for kid, d in sorted(kunos_to_matches.items()):
    tests = d['all_tests']
    by_game = {}
    for g, code, trk in tests:
        by_game.setdefault(g, []).append(code)
    test_summary = ", ".join([f"{g}: {', '.join(codes)}" for g, codes in sorted(by_game.items())])
    print(f"* **{d['name']}** (`{kid}`)")
    print(f"    - GT Variants: {', '.join(d['gt_variants'])}")
    print(f"    - Tests ({len(tests)}): {test_summary}")


print("\n" + "="*80)
print("3. TESTS WHERE BOTH CAR AND TRACK ARE OFFICIAL KUNOS CONTENT")
print("="*80)

perfect_matches = []
for m in car_matches:
    for g, code, trk in m['tests']:
        tr_low = trk.lower()
        if 'dragon' in tr_low: continue
        matched_trk = None
        if 'nordschleife' in tr_low:
            matched_trk = 'Nürburgring Nordschleife (`ks_nordschleife`)'
        else:
            for tname, pats, tid in kunos_tracks:
                if tname == 'Nürburgring Nordschleife': continue
                if any(p in tr_low for p in pats):
                    matched_trk = f"{tname} (`{tid}`)"
                    break
        if matched_trk:
            perfect_matches.append({
                'game': g,
                'code': code,
                'gt_car': m['gt_car'],
                'kunos_car': m['kunos_name'],
                'kunos_track': matched_trk,
                'track_name': trk
            })

print(f"Total 100% Kunos Matches (Car AND Track): {len(perfect_matches)}")
for pm in sorted(perfect_matches, key=lambda x: (x['game'], x['code'])):
    print(f"* [{pm['game']} {pm['code']}] **{pm['kunos_car']}** at **{pm['kunos_track']}** (GT: {pm['gt_car']})")

