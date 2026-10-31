import re
import json
from pathlib import Path
from build_car_specs import match_car, get_layout

def parse_time_value(time_str):
    s = time_str.strip()
    if not s or s == "N/A":
        return None, "unknown", {}
    
    if re.match(r'^\d+(?:st|nd|rd|th)$', s, re.IGNORECASE):
        return None, "position", {}
        
    if "Any time" in s:
        return None, "condition", {}

    if re.match(r'^\d+$', s) and int(s) < 10:
        return None, "pace_car", {}

    def extract_sec(chunk):
        chunk = chunk.strip()
        chunk_clean = re.sub(r'(?:s|sec)$', '', chunk).strip()
        m = re.search(r'(\d+):(\d+(?:\.\d+)?)', chunk_clean)
        if m:
            minutes = int(m.group(1))
            seconds = float(m.group(2))
            return round(minutes * 60 + seconds, 3)
        m2 = re.search(r'^(\d+(?:\.\d+)?)$', chunk_clean)
        if m2:
            val = float(m2.group(1))
            if '.' in chunk_clean or val >= 10:
                return round(val, 3)
        return None

    parts = [p.strip() for p in s.split(';') if p.strip()]
    variants = {}
    primary_seconds = None

    for part in parts:
        reg_match = re.search(r'\(([^)]+)\)', part)
        region = reg_match.group(1) if reg_match else "default"
        time_part = re.sub(r'\([^)]+\)', '', part).strip()
        sec = extract_sec(time_part)
        if sec is not None:
            variants[region] = sec
            if primary_seconds is None:
                primary_seconds = sec

    if primary_seconds is not None:
        return primary_seconds, "time", variants

    return None, "unknown", variants


def parse_pw_value(pw_str):
    s = pw_str.strip()
    m = re.search(r'([\d.]+)\s*(?:kg/hp|kg/ps)', s, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            return None
    return None


def parse_car_year(car_str):
    m = re.search(r"'(\d{2})\b", car_str)
    if m:
        yy = int(m.group(1))
        year = (1900 + yy) if yy >= 40 else (2000 + yy)
        return year
    m4 = re.search(r'\b(19\d{2}|20\d{2})\b', car_str)
    if m4:
        return int(m4.group(1))
    return None


def convert_markdown_to_json(md_path, json_path):
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    current_section = None
    current_game = None
    current_license = None
    tests = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('## '):
            current_section = stripped[3:].strip()
            m = re.match(r'^(GT\d+)\s+(.+)$', current_section)
            if m:
                current_game = m.group(1)
                current_license = m.group(2)
            else:
                current_game = "Unknown"
                current_license = current_section
            continue

        if stripped.startswith('|') and not stripped.startswith('| Test') and not stripped.startswith('|---'):
            columns = [c.strip() for c in stripped.split('|')[1:-1]]
            if len(columns) < 9:
                continue

            test_field = columns[0]
            car = columns[1]
            pw = columns[2]
            engine = columns[3]
            drivetrain = columns[4]
            track = columns[5]
            gold_raw = columns[6]
            silver_raw = columns[7]
            bronze_raw = columns[8]

            if ' - ' in test_field:
                code, title = test_field.split(' - ', 1)
                code = code.strip()
                title = title.strip()
            else:
                code = test_field.strip()
                title = ""

            clean_code = re.sub(r'[^A-Za-z0-9_.-]', '_', code)
            clean_game = current_game or "GT"
            unique_id = f"{clean_game}_{clean_code}"

            gold_sec, gold_type, gold_vars = parse_time_value(gold_raw)
            silver_sec, silver_type, silver_vars = parse_time_value(silver_raw)
            bronze_sec, bronze_type, bronze_vars = parse_time_value(bronze_raw)

            entry = {
                "id": unique_id,
                "game": current_game,
                "license": current_license,
                "section": current_section,
                "code": code,
                "title": title,
                "test": test_field,
                "car": car,
                "car_year": parse_car_year(car),
                "pw": pw,
                "pw_kg_hp": parse_pw_value(pw),
                "engine": engine,
                "drivetrain": drivetrain,
                "track": track,
                "gold": gold_raw,
                "silver": silver_raw,
                "bronze": bronze_raw,
                "gold_seconds": gold_sec,
                "silver_seconds": silver_sec,
                "bronze_seconds": bronze_sec,
                "target_type": gold_type if gold_type != "unknown" else silver_type,
            }

            time_variants = {}
            if gold_vars and len(gold_vars) > 1:
                time_variants["gold"] = gold_vars
            if silver_vars and len(silver_vars) > 1:
                time_variants["silver"] = silver_vars
            if bronze_vars and len(bronze_vars) > 1:
                time_variants["bronze"] = bronze_vars
            if time_variants:
                entry["regional_variants"] = time_variants

            tests.append(entry)

    # Enrich progression, specs, HP, and drivetrain layout
    by_game = {}
    for t in tests:
        by_game.setdefault(t['game'], []).append(t)

    for g, g_tests in by_game.items():
        for idx, t in enumerate(g_tests, 1):
            t['test_progression'] = idx
            matched_hp, matched_weight, def_eng, def_drivetrain = match_car(t['car'])
            if not t.get('engine') or t['engine'] == 'Unknown':
                t['engine'] = def_eng
            if not t.get('drivetrain') or t['drivetrain'] == 'Unknown':
                t['drivetrain'] = def_drivetrain
                
            t['hp'] = matched_hp
            t['weight_kg'] = matched_weight
            if t.get('pw_kg_hp') is None:
                t['pw_kg_hp'] = round(matched_weight / matched_hp, 2)
            t['pw'] = t['pw_kg_hp']
            t['drivetrain_layout'] = get_layout(t['engine'], t['drivetrain'])

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(tests, f, indent=2, ensure_ascii=False)

    print(f"Successfully converted {len(tests)} tests to {json_path}")
    return tests

if __name__ == '__main__':
    root = Path(__file__).resolve().parent.parent
    md_file = root / 'docs' / 'Gran_Turismo_License_Tests.md'
    json_file = root / 'docs' / 'Gran_Turismo_License_Tests.json'
    convert_markdown_to_json(md_file, json_file)
