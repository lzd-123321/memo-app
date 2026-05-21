# Memo — 桌面便签

A translucent, always-available desktop memo app built with Python + tkinter. Stays on your desktop, hides when you work, comes back with a hotkey.

## Features

- **Translucent window** — semi-transparent, sits on your desktop like a widget
- **Always available** — `Ctrl + Shift + M` to show/hide instantly
- **Todo list with checkboxes** — check off items, they animate and move to "Done"
- **Two tabs** — Active / Completed, switch at the top
- **Drag & resize** — drag by title bar, resize by bottom-right corner
- **Auto-save** — saves on hide/close, restores on launch
- **Zero dependencies** — only Python standard library

## Quick Start

```bash
python memo.py
```

Requires Python 3.7+. No pip install needed.

## Usage

| Action | How |
|--------|-----|
| Add task | Type in the input bar, press Enter or click ＋ |
| Complete task | Click the checkbox |
| Switch tabs | Click `[待办事项]` / `[已完成 N]` |
| Move window | Drag the title bar |
| Resize | Drag the bottom bar or bottom-right corner `◢` |
| Hide window | Click `✕` |
| Show window | `Ctrl + Shift + M` |
| Reset position | `Ctrl + R` |
| Clear list | Click `清空` button |
| Fully quit | Right-click title bar → `彻底退出` |

## File Structure

```
memo-app/
├── memo.py          # the app (single file)
├── memo_data.json   # your data (auto-generated)
└── README.md
```

## License

MIT
