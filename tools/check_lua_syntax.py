#!/usr/bin/env python3
import sys
import re

def check_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        code = f.read()

    # remove multi-line comments
    code = re.sub(r'--\[\[.*?\]\]', '', code, flags=re.DOTALL)
    # remove single-line comments
    code = re.sub(r'--[^\n]*', '', code)
    # remove strings
    code = re.sub(r'"(\\.|[^"\\])*"', '""', code)
    code = re.sub(r"'(\\.|[^'\\])*'", "''", code)

    # Find tokens with line numbers
    lines = code.split('\n')
    stack = []
    for line_no, line in enumerate(lines, 1):
        line_clean = re.sub(r'--.*', '', line)
        line_clean = re.sub(r'"(\\.|[^"\\])*"', '""', line_clean)
        line_clean = re.sub(r"'(\\.|[^'\\])*'", "''", line_clean)
        # If line contains 'elseif ... then', don't push a new 'then'
        # Tokenize keywords
        line_tokens = re.findall(r'\b(?:function|elseif|then|do|repeat|until|end)\b', line_clean)
        for i, t in enumerate(line_tokens):
            if t == 'then':
                # Check if preceded by 'elseif'
                if i > 0 and line_tokens[i-1] == 'elseif':
                    pass # continues current 'if/then' block
                else:
                    stack.append((t, line_no, line.strip()))
            elif t in ('function', 'do', 'repeat'):
                stack.append((t, line_no, line.strip()))
            elif t == 'until':
                if stack and stack[-1][0] == 'repeat':
                    stack.pop()
                else:
                    print(f"Error at line {line_no}: Unmatched 'until'")
                    return False
            elif t == 'end':
                if stack and stack[-1][0] in ('function', 'then', 'do'):
                    stack.pop()
                else:
                    print(f"Error at line {line_no}: Unmatched 'end'! Stack: {stack}")
                    return False

    if stack:
        print(f"Error in {path}: {len(stack)} unclosed block(s):")
        for t, l_no, text in stack:
            print(f"  Line {l_no} [{t}]: {text}")
        return False

    print(f"[OK] {path}: Balanced syntax blocks across {len(lines)} lines")
    return True

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'lua/ui/gt_license_hud.lua'
    success = check_file(target)
    sys.exit(0 if success else 1)
