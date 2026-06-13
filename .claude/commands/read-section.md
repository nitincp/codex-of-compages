---
name: read-section
description: Read a specific section from a markdown file using a file#anchor reference. Use whenever a doc link includes #anchor notation, instead of loading the whole file.
---

Run `python3 .claude/commands/scripts/read_section.py $ARGUMENTS` and display the output.

The script extracts from the matched heading to the next heading of equal or higher level — nothing more. Only that section enters context.

**Usage:**
```bash
python3 .claude/commands/scripts/read_section.py ARCHITECTURE.md#graph-architecture--gnn-first
python3 .claude/commands/scripts/read_section.py CLAUDE.md#milestone-completion-checklist
python3 .claude/commands/scripts/read_section.py BACKLOG.md#done
```

**List all anchors in a file** (when the anchor is unknown):
```bash
python3 .claude/commands/scripts/read_section.py ARCHITECTURE.md#list
```

If the anchor is not found, the script exits with an error and prints all available anchors for that file.

**Anchor format** matches GitHub's rendering: lowercase, non-word chars stripped, spaces → hyphens (each space individually, so em dashes leave a double hyphen: `--`).
