#!/usr/bin/env python3
"""
Convert Flipper Zero BadUSB (DuckyScript) payloads -> Evil Crow Cable Wind syntax.

Usage:
    python3 convert_flipper_payloads.py <input_dir> [output_dir] [--winprint]

- Recurses <input_dir> for *.txt payloads (Flipper DuckyScript).
- Writes converted payloads to <output_dir> (default: <input_dir>_evilcrow),
  mirroring the folder layout, ready to paste/upload into the Evil Crow web panel.
- Writes <output_dir>/CONVERSION_REPORT.txt with a per-file status:
    OK       - clean 1:1 conversion
    EMULATED - used injected Delays (DEFAULT_DELAY) or expanded REPEAT
    REVIEW   - had unsupported/unrecognized commands (dropped) -> needs a look
- Unsupported source lines are dropped from the output and listed in the report
  with their line number and reason.

--winprint : emit WinPrint/WinPrintLine (layout-agnostic, Windows-only targets)
             instead of Print/PrintLine.

NOTE: still set the matching keyboard layout in the Evil Crow web panel (EN_US,
ES_ES, ...) unless you use --winprint on a Windows target.
"""
import sys, os

MODIFIERS = {
    'CTRL': 'KEY_LEFT_CTRL', 'CONTROL': 'KEY_LEFT_CTRL',
    'ALT': 'KEY_LEFT_ALT',
    'SHIFT': 'KEY_LEFT_SHIFT',
    'GUI': 'KEY_LEFT_GUI', 'WINDOWS': 'KEY_LEFT_GUI', 'WIN': 'KEY_LEFT_GUI', 'COMMAND': 'KEY_LEFT_GUI',
}

NAMED_KEYS = {
    'ENTER': 'KEY_ENTER', 'RETURN': 'KEY_ENTER',
    'TAB': 'KEY_TAB', 'SPACE': 'KEY_SPACE',
    'ESC': 'KEY_ESC', 'ESCAPE': 'KEY_ESC',
    'DELETE': 'KEY_DELETE', 'DEL': 'KEY_DELETE',
    'BACKSPACE': 'KEY_BACKSPACE',
    'UP': 'KEY_UP_ARROW', 'UPARROW': 'KEY_UP_ARROW',
    'DOWN': 'KEY_DOWN_ARROW', 'DOWNARROW': 'KEY_DOWN_ARROW',
    'LEFT': 'KEY_LEFT_ARROW', 'LEFTARROW': 'KEY_LEFT_ARROW',
    'RIGHT': 'KEY_RIGHT_ARROW', 'RIGHTARROW': 'KEY_RIGHT_ARROW',
    'HOME': 'KEY_HOME', 'END': 'KEY_END', 'INSERT': 'KEY_INSERT',
    'UP_ARROW': 'KEY_UP_ARROW', 'DOWN_ARROW': 'KEY_DOWN_ARROW',
    'LEFT_ARROW': 'KEY_LEFT_ARROW', 'RIGHT_ARROW': 'KEY_RIGHT_ARROW',
    'PAGEUP': 'KEY_PAGE_UP', 'PAGEDOWN': 'KEY_PAGE_DOWN',
    'PAGE_UP': 'KEY_PAGE_UP', 'PAGE_DOWN': 'KEY_PAGE_DOWN',
    'CAPSLOCK': 'KEY_CAPS_LOCK', 'NUMLOCK': 'KEY_NUM_LOCK', 'SCROLLLOCK': 'KEY_SCROLL_LOCK',
    'CAPS_LOCK': 'KEY_CAPS_LOCK', 'NUM_LOCK': 'KEY_NUM_LOCK', 'SCROLL_LOCK': 'KEY_SCROLL_LOCK',
    'PRINTSCREEN': 'KEY_PRINT_SCREEN', 'PRINT_SCREEN': 'KEY_PRINT_SCREEN',
    'BREAK': 'KEY_PAUSE', 'PAUSE': 'KEY_PAUSE',
    'MENU': 'KEY_MENU', 'APP': 'KEY_MENU',
}
for _i in range(1, 13):
    NAMED_KEYS['F%d' % _i] = 'KEY_F%d' % _i

# Flipper/DuckyScript commands with no Evil Crow equivalent -> dropped + reported.
# (ALTSTRING is handled -> WinPrint; only single-codepoint ALT* remain unsupported.)
UNSUPPORTED = {
    'ALTCHAR', 'ALTCODE', 'ALTCODEPOINT',
    'WAITFORBUTTONPRESS', 'WAIT_FOR_BUTTON_PRESS',
    'LED', 'SYSRQ', 'INJECT_MOD', 'GLOBE',
    'VOLUP', 'VOLDOWN', 'VOLUME_UP', 'VOLUME_DOWN', 'MUTE', 'PLAYPAUSE', 'PLAY',
    'STOP', 'NEXTTRACK', 'PREVTRACK', 'BRIGHTNESS_UP', 'BRIGHTNESS_DOWN', 'MEDIA',
    # DuckyScript 2.0 flow control (not supported by the interpreter)
    'VAR', 'IF', 'ELSE', 'END_IF', 'WHILE', 'END_WHILE', 'FUNCTION', 'END_FUNCTION', 'DEFINE',
}


def map_key(tok):
    """A single Flipper key token -> Evil Crow key name/char, or None if unknown."""
    u = tok.upper()
    if u in NAMED_KEYS:
        return NAMED_KEYS[u]
    if len(tok) == 1:
        return tok  # printable char; keyboard layout handles it
    return None


def convert_combo(tokens):
    """['GUI','r'] / ['CTRL-ALT','DELETE'] / ['TAB'] -> (lines, ok)."""
    # Expand hyphenated combos (CTRL-ALT, GUI-SHIFT-s) into separate tokens.
    expanded = []
    for t in tokens:
        expanded.extend([p for p in t.split('-') if p] if ('-' in t and len(t) > 1) else [t])
    tokens = expanded

    keys = [t for t in tokens if t.upper() not in MODIFIERS]
    mods = [MODIFIERS[t.upper()] for t in tokens if t.upper() in MODIFIERS]

    if not mods and len(keys) == 1:  # bare key / char
        k = map_key(keys[0])
        return ((['PressRelease %s' % k], True) if k else (None, False))
    if not keys and mods:            # modifiers only (e.g. GUI alone)
        if len(mods) == 1:
            return (['PressRelease %s' % mods[0]], True)
        return ([('Press %s' % m) for m in mods] + ['Release'], True)

    out, ok = ['Press %s' % m for m in mods], True
    for k in keys:
        mk = map_key(k)
        if mk is None:
            ok = False
        else:
            out.append('PressRelease %s' % mk)
    out.append('Release')
    return (out, ok)


def convert_text(text, winprint=False):
    PRINT = 'WinPrint' if winprint else 'Print'
    PRINTLN = 'WinPrintLine' if winprint else 'PrintLine'
    out, report = [], []            # report: (lineno, text, kind)  kind in {'drop','emulate'}
    default_delay = 0
    last_block = []
    lines = text.splitlines()
    i = 0

    while i < len(lines):
        lineno = i + 1
        s = lines[i].strip()
        i += 1
        if s == '' or s.startswith('//') or s.startswith('#'):
            continue
        parts = s.split(' ', 1)
        cu = parts[0].upper()
        arg = parts[1] if len(parts) > 1 else ''
        block = None

        if cu.startswith('REM') or cu in ('END_STRING', 'END_STRINGLN', 'END_REM',
                                          'ATTACKMODE', 'DUCKY_LANG', 'LOCALE'):
            continue                                          # comments / hw-mode / metadata
        elif cu == 'HOLD':
            m = MODIFIERS.get(arg.strip().upper())
            k = m or map_key(arg.strip())
            if k is None:
                report.append((lineno, s, 'drop')); continue
            block = ['Press %s' % k]
        elif cu == 'RELEASE':
            block = ['Release']                               # Evil Crow releases all held keys
        elif cu in ('STRING', 'STR') and arg != '':
            block = ['%s %s' % (PRINT, arg)]
        elif cu in ('STRINGLN', 'STRLN') and arg != '':
            block = ['%s %s' % (PRINTLN, arg)]
        elif cu in ('STRING', 'STR', 'STRINGLN', 'STRLN'):   # multi-line block, no arg
            end = 'END_STRINGLN' if cu in ('STRINGLN', 'STRLN') else 'END_STRING'
            block = []
            while i < len(lines) and lines[i].strip().upper() != end:
                block.append('%s %s' % (PRINTLN, lines[i]))   # each block line + ENTER
                i += 1
            if i < len(lines):
                i += 1                                        # consume the END_ line
        elif cu == 'ALTSTRING':
            block = ['WinPrint %s' % arg]   # ~ alt-code string: Windows layout-agnostic
        elif cu == 'DELAY':
            block = ['Delay %s' % arg.strip()]
        elif cu in ('DEFAULT_DELAY', 'DEFAULTDELAY'):
            try:
                default_delay = int(arg.strip())
            except ValueError:
                default_delay = 0
            report.append((lineno, s, 'emulate'))
            continue
        elif cu in ('ENTER', 'RETURN'):
            block = ['PressRelease KEY_ENTER']
        elif cu == 'REPEAT':
            try:
                n = int(arg.strip())
            except ValueError:
                n = 0
            for _ in range(n):
                out.extend(last_block)
            report.append((lineno, s, 'emulate'))
            continue
        elif cu in UNSUPPORTED:
            report.append((lineno, s, 'drop'))
            continue
        else:
            block, ok = convert_combo(s.split())
            if block is None or not ok:
                report.append((lineno, s, 'drop'))
                continue

        # DEFAULT_DELAY emulation: inject a Delay after each command (not pure Delays)
        if default_delay > 0 and not (len(block) == 1 and block[0].startswith('Delay ')):
            block = block + ['Delay %d' % default_delay]

        out.extend(block)
        if block:
            last_block = block

    return out, report


def status_of(report):
    if any(k == 'drop' for _, _, k in report):
        return 'REVIEW'
    if any(k == 'emulate' for _, _, k in report):
        return 'EMULATED'
    return 'OK'


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    winprint = '--winprint' in sys.argv
    if not args:
        print(__doc__)
        sys.exit(1)
    in_dir = os.path.abspath(args[0])
    out_dir = os.path.abspath(args[1]) if len(args) > 1 else in_dir.rstrip('/') + '_evilcrow'
    os.makedirs(out_dir, exist_ok=True)

    results = []  # (relpath, status, report)
    for root, _, files in os.walk(in_dir):
        for fn in files:
            if not fn.lower().endswith('.txt'):
                continue
            src = os.path.join(root, fn)
            rel = os.path.relpath(src, in_dir)
            try:
                text = open(src, 'r', encoding='utf-8', errors='replace').read()
            except Exception as e:
                results.append((rel, 'ERROR', [(0, str(e), 'drop')]))
                continue
            lines, report = convert_text(text, winprint)
            dst = os.path.join(out_dir, rel)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines) + ('\n' if lines else ''))
            results.append((rel, status_of(report), report))

    # Report
    ok = sum(1 for _, s, _ in results if s == 'OK')
    emu = sum(1 for _, s, _ in results if s == 'EMULATED')
    rev = sum(1 for _, s, _ in results if s == 'REVIEW')
    err = sum(1 for _, s, _ in results if s == 'ERROR')
    rep_path = os.path.join(out_dir, 'CONVERSION_REPORT.txt')
    with open(rep_path, 'w', encoding='utf-8') as f:
        f.write("Flipper -> Evil Crow Cable Wind conversion report\n")
        f.write("input : %s\n" % in_dir)
        f.write("output: %s\n" % out_dir)
        f.write("total %d files | OK %d | EMULATED %d | REVIEW %d | ERROR %d\n"
                % (len(results), ok, emu, rev, err))
        f.write("=" * 70 + "\n\n")
        for rel, st, report in sorted(results, key=lambda x: (x[1] != 'REVIEW', x[0])):
            if st == 'OK':
                continue  # only detail the ones that need attention
            f.write("[%s] %s\n" % (st, rel))
            for ln, txt, kind in report:
                tag = 'DROPPED' if kind == 'drop' else 'emulated'
                f.write("    line %-4s %-8s : %s\n" % (ln, tag, txt))
            f.write("\n")
        if rev == 0 and err == 0:
            f.write("No files need manual review.\n")

    print("Converted %d payloads -> %s" % (len(results), out_dir))
    print("  OK %d | EMULATED %d | REVIEW %d | ERROR %d" % (ok, emu, rev, err))
    print("  report: %s" % rep_path)
    if rev:
        print("\n  Needs review (had unsupported commands):")
        for rel, st, _ in sorted(results):
            if st == 'REVIEW':
                print("    - %s" % rel)


if __name__ == '__main__':
    main()
