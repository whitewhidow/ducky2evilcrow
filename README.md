# ducky2evilcrow

Convert **Flipper Zero / Hak5 Rubber Ducky BadUSB payloads (DuckyScript)** into the
**[Evil Crow Cable Wind](https://github.com/joelsernamoreno/EvilCrowCable-Wind)**
native command syntax.

The Evil Crow Cable Wind does **not** use DuckyScript — it has its own interpreter
(`Print`, `PressRelease`, `Delay`, `GuiR`, …). So the thousands of existing
DuckyScript payloads won't run on it as-is. This tool translates them, and **flags
exactly which files use features the Evil Crow can't do** so you know what needs a
manual look instead of silently shipping a broken payload.

## 🌐 Use it in your browser — no install

**→ https://whitewhidow.github.io/ducky2evilcrow/**

A static page (runs 100% client-side — nothing is uploaded): paste a payload and get
the converted output live, or drag-drop a whole folder of `.txt` files and download
them (or a `.zip`), each with its conversion status. Same logic as the Python CLI below.

> ⚠️ For authorized security research / testing only. Use exclusively on devices and
> accounts you own or have explicit permission to test.

## Usage

```bash
python3 convert_flipper_payloads.py <input_dir> [output_dir] [--winprint]
```

- Recurses `<input_dir>` for `*.txt` DuckyScript payloads.
- Writes converted payloads to `<output_dir>` (default `<input_dir>_evilcrow`),
  mirroring the folder layout — ready to paste/upload into the Evil Crow web panel.
- Writes `<output_dir>/CONVERSION_REPORT.txt` with a per-file status and the line
  numbers/reasons for anything it couldn't convert.
- `--winprint` emits `WinPrint`/`WinPrintLine` (layout-agnostic, **Windows targets
  only**) instead of `Print`/`PrintLine`.

You can also point it at a single file (it'll still scan a directory, so pass the
folder the file lives in).

### Per-file status in the report

| Status | Meaning |
|---|---|
| `OK` | Clean 1:1 conversion |
| `EMULATED` | Used injected `Delay`s (`DEFAULT_DELAY`) or expanded `REPEAT` — works, just not literal |
| `REVIEW` | Had unsupported/unrecognized commands (dropped) — **look at this one** |
| `ERROR` | File couldn't be read |

## Command mapping

| DuckyScript (Flipper/Hak5) | Evil Crow Cable Wind |
|---|---|
| `STRING text` | `Print text` |
| `STRINGLN text` | `PrintLine text` |
| `STRING` … `END_STRING` (multi-line) | `PrintLine` per line |
| `ALTSTRING text` | `WinPrint text` (Windows, layout-agnostic) |
| `DELAY 500` | `Delay 500` |
| `DEFAULT_DELAY n` | *emulated:* a `Delay n` injected after each command |
| `ENTER` | `PressRelease KEY_ENTER` |
| `GUI r` / `WINDOWS r` | `Press KEY_LEFT_GUI` / `PressRelease r` / `Release` |
| `CTRL-ALT DELETE` (hyphenated mods) | `Press KEY_LEFT_CTRL` / `Press KEY_LEFT_ALT` / `PressRelease KEY_DELETE` / `Release` |
| `HOLD key` / `RELEASE` | `Press <key>` / `Release` (Release frees all held keys) |
| `TAB` `SPACE` `ESC` `DELETE` `UP` `F5` … | `PressRelease KEY_TAB` / `KEY_SPACE` / `KEY_ESC` / … |
| `REPEAT n` | *emulated:* previous block duplicated n times |
| `REM …` | dropped (comment) |

Modifiers map to `KEY_LEFT_CTRL` / `KEY_LEFT_ALT` / `KEY_LEFT_GUI` / `KEY_LEFT_SHIFT`
(and their `RIGHT_` forms), and all named/arrow/F-keys map to the Evil Crow `KEY_…`
names.

## Not convertible (flagged `REVIEW`)

The Evil Crow interpreter is DuckyScript-**1.0**-style: no variables, no logic. These
are dropped and reported — the payload needs a manual rewrite:

- **DuckyScript 2.0/3.0 flow control & variables:** `VAR` `DEFINE` `IF`/`END_IF`
  `ELSE` `WHILE`/`END_WHILE` `FUNCTION`/`END_FUNCTION`, `$variables`, `SEND_MULTI()`, …
- **`WAIT_FOR_BUTTON_PRESS`** — the Evil Crow cable has no button.
- **`ALTCHAR` / `ALTCODE`** — single Alt-numpad codepoints (no equivalent).
- **`LED` / `SYSRQ` / media & consumer keys** — no equivalent.

`ATTACKMODE`, `REM`/`END_REM` and metadata lines are ignored silently.

## Keyboard layout

Set the matching **keyboard layout** in the Evil Crow web panel (`EN_US`, `ES_ES`,
`DE_DE`, … — 17 available) to whatever a payload was written for, or special
characters come out wrong. For Windows targets you can instead convert with
`--winprint` to sidestep layout issues entirely.

## Example

`examples/flipper_input.txt` → `examples/evilcrow_output.txt`. Input:

```
DEFAULT_DELAY 200
DELAY 1000
GUI r
STRING powershell
ENTER
CTRL-ALT t
```

becomes:

```
Delay 1000
Press KEY_LEFT_GUI
PressRelease r
Release
Delay 200
Print powershell
Delay 200
PressRelease KEY_ENTER
Delay 200
Press KEY_LEFT_CTRL
Press KEY_LEFT_ALT
PressRelease t
Release
Delay 200
```

## Where to get payloads

- **Native Evil Crow (run as-is):** the official repo's
  [`payloads/`](https://github.com/joelsernamoreno/EvilCrowCable-Wind/tree/main/payloads)
  (by OS — windows/linux/macos/android/ios).
- **DuckyScript to convert with this tool:**
  [`hak5/usbrubberducky-payloads`](https://github.com/hak5/usbrubberducky-payloads),
  [`I-Am-Jakoby/Flipper-Zero-BadUSB`](https://github.com/I-Am-Jakoby/Flipper-Zero-BadUSB),
  and other Flipper/Ducky payload collections.

## Credits

- Evil Crow Cable Wind hardware + firmware © Joel Serna Moreno —
  <https://github.com/joelsernamoreno/EvilCrowCable-Wind>.
- Converter: whitewhidow. MIT licensed.
