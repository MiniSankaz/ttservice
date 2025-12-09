# .claude/ - Claude Code Resume System

This directory contains context files that allow Claude Code to resume conversations
seamlessly across different machines and sessions.

## How It Works

When you start a new Claude Code session on any machine:

1. Claude reads `CLAUDE.md` in project root (project overview)
2. Claude reads `.claude/PROJECT_CONTEXT.md` (static project knowledge)
3. Claude reads `.claude/CURRENT_STATE.md` (current work state)
4. Claude can continue where the last session left off

## Files

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `PROJECT_CONTEXT.md` | Static project knowledge, architecture decisions | Rarely (major changes only) |
| `CURRENT_STATE.md` | Current work state, pending tasks, recent changes | Every session end |
| `DECISIONS.md` | Important technical decisions and rationale | When decisions are made |
| `KNOWN_ISSUES.md` | Known bugs and workarounds | As discovered |

## Usage

### Starting a New Session
```
Just say: "อ่าน .claude/ แล้วทำงานต่อ" or "Resume from .claude/"
```

### Ending a Session
```
Just say: "อัพเดต .claude/ และ commit"
```

### On New Machine
```bash
git clone <repo>
cd transcriptor-pipeline-pilot
# Start Claude Code - it will read .claude/ automatically
```

## Best Practices

1. **Always commit .claude/ changes** - This ensures all machines have the same context
2. **Update CURRENT_STATE.md** before ending session
3. **Keep PROJECT_CONTEXT.md concise** - Only essential info
4. **Use DECISIONS.md** for "why" questions
