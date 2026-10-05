import re
from pathlib import Path

def lint_lua(filepath: Path):
    content = filepath.read_text(encoding='utf-8')
    # Remove block comments
    clean = re.sub(r'--\[\[.*?\]\]', '', content, flags=re.DOTALL)
    # Remove single line comments
    clean = re.sub(r'--[^\n]*', '', clean)
    # Remove multi-line strings
    clean = re.sub(r'\[\[.*?\]\]', '""', clean, flags=re.DOTALL)
    # Remove single and double quoted strings
    clean = re.sub(r'"(\\.|[^"\\])*"', '""', clean)
    clean = re.sub(r"'(\\.|[^'\\])*'", "''", clean)

    # In Lua:
    # 'if' starts a conditional, ended by 'end' (regardless of how many 'elseif ... then' or 'else' are inside)
    # 'for' starts a loop with 'do', ended by 'end'
    # 'while' starts a loop with 'do', ended by 'end'
    # 'do' (standalone) starts a block, ended by 'end'
    # 'function' starts a function, ended by 'end'
    
    # Let's tokenize keywords
    tokens = re.findall(r'\b(if|for|while|do|function|end)\b', clean)
    stack = []
    errors = []
    
    # Note: 'for ... do' and 'while ... do' have both 'for'/'while' AND 'do'.
    # In Lua, the 'for' loop is closed by ONE 'end'.
    # So if we see 'for' or 'while', the following 'do' belongs to that loop, not a standalone 'do'.
    
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in ('for', 'while'):
            # The next 'do' is part of this loop
            stack.append(tok)
            # Find matching 'do'
            i += 1
            while i < len(tokens) and tokens[i] != 'do':
                # Might have nested functions or expressions before do, but typically 'do' follows
                i += 1
            # 'do' found for this loop
        elif tok == 'if':
            stack.append('if')
        elif tok == 'do':
            stack.append('do')
        elif tok == 'function':
            stack.append('function')
        elif tok == 'end':
            if not stack:
                errors.append("Unmatched 'end'")
            else:
                stack.pop()
        i += 1

    if stack:
        errors.append(f"Unclosed blocks: {stack}")

    # Check parenthetical balance
    brackets = {'(': ')', '[': ']', '{': '}'}
    p_stack = []
    for line_num, line in enumerate(clean.splitlines(), 1):
        for char in line:
            if char in '([{':
                p_stack.append((char, line_num))
            elif char in ')]}':
                if not p_stack:
                    errors.append(f"Unmatched closing '{char}' on line {line_num}")
                else:
                    last_open, last_line = p_stack.pop()
                    if brackets[last_open] != char:
                        errors.append(f"Mismatched bracket '{last_open}' (line {last_line}) and '{char}' (line {line_num})")
    if p_stack:
        errors.append(f"Unclosed brackets: {p_stack}")

    return errors

def main():
    files = [
        Path('lua/engine/gt_physics_hooks.lua'),
        Path('lua/engine/gt_adjudicator.lua'),
        Path('lua/engine/gt_session_reset.lua'),
        Path('lua/engine/gt_license_engine.lua'),
        Path('lua/ui/gt_license_hud.lua'),
        Path('lua/ui/gt_render_gates.lua'),
        Path('lua/ui/gt_audio_manager.lua'),
    ]
    all_ok = True
    for f in files:
        errs = lint_lua(f)
        if errs:
            print(f"FAIL: {f} -> {errs}")
            all_ok = False
        else:
            print(f"PASS: {f} syntax structure is clean!")

    if all_ok:
        print("\nALL LUA ENGINE & UI FILES VALIDATED CLEANLY!")

if __name__ == '__main__':
    main()
