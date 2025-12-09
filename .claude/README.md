# .claude/ - Claude Code Resume System

This directory contains context files that allow Claude Code to resume conversations
seamlessly across different machines and sessions.

## Quick Start

### On New Machine (After Clone)
```bash
# 1. Install git hooks (one-time setup)
./.claude/scripts/install_hooks.sh

# 2. View current state
./.claude/scripts/resume.sh

# 3. Start Claude Code
claude

# 4. Say this to resume:
"อ่าน .claude/ แล้วทำงานต่อ"
```

### Before Ending Session
```bash
# Option 1: Manual save
./.claude/scripts/save_session.sh "What you did this session"

# Option 2: Just push (auto-save via hook)
git push  # pre-push hook will auto-save state
```

## How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Git Repository                            │
├─────────────────────────────────────────────────────────────┤
│  .claude/                                                   │
│  ├── PROJECT_CONTEXT.md  ← Static knowledge (rarely changes)│
│  ├── CURRENT_STATE.md    ← Session state (auto-updated)     │
│  ├── DECISIONS.md        ← Decision log                     │
│  ├── KNOWN_ISSUES.md     ← Bug tracking                     │
│  └── scripts/                                               │
│      ├── resume.sh       ← Show current state               │
│      ├── save_session.sh ← Manual save before push          │
│      └── install_hooks.sh← Install git hooks                │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   Git Push        │
                    │   (pre-push hook) │
                    └─────────┬─────────┘
                              │
                    Auto-saves CURRENT_STATE.md
```

## Files

| File | Purpose | Update Frequency |
|------|---------|------------------|
| `PROJECT_CONTEXT.md` | Static project knowledge, architecture | Rarely |
| `CURRENT_STATE.md` | Current work state, pending tasks | Every push (auto) |
| `DECISIONS.md` | Technical decisions and rationale | When decisions made |
| `KNOWN_ISSUES.md` | Known bugs and workarounds | As discovered |

## Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `resume.sh` | Display current state for resume | After clone/checkout |
| `save_session.sh` | Manual session save with summary | Before ending work |
| `install_hooks.sh` | Install git hooks | One-time on new machine |

## Git Hooks (Auto-installed)

| Hook | Trigger | Action |
|------|---------|--------|
| `pre-push` | Before `git push` | Auto-save CURRENT_STATE.md |
| `post-checkout` | After branch switch | Show resume reminder |

## Best Practices

1. **Run `install_hooks.sh` after clone** - Enables auto-save on push
2. **Use `resume.sh` to see current state** - Quick overview before starting
3. **Let hooks handle state saving** - Just push normally, state is auto-saved
4. **Keep PROJECT_CONTEXT.md stable** - Only update for major architecture changes
5. **Use DECISIONS.md for "why"** - Document reasoning for future reference

## Portable Workflow

```
Machine A                    Git Remote                    Machine B
─────────                    ──────────                    ─────────
Work on feature
     │
     └──► git push ──────────► [auto-save state] ────────► git pull
         (pre-push hook)                                      │
                                                              ▼
                                                         ./resume.sh
                                                              │
                                                              ▼
                                                         Start Claude
                                                              │
                                                              ▼
                                                    "อ่าน .claude/..."
                                                              │
                                                              ▼
                                                      Continue work!
```
