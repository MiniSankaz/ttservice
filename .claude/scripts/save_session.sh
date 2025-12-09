#!/bin/bash
# =============================================================================
# save_session.sh - Save Claude Code Session State Before Push
# =============================================================================
# This script saves the current conversation state and prepares for git push.
# Run this BEFORE pushing code to ensure session state is preserved.
#
# Usage: ./.claude/scripts/save_session.sh [commit_message]
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"
STATE_FILE="$CLAUDE_DIR/CURRENT_STATE.md"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           💾 SAVE CLAUDE CODE SESSION                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

cd "$PROJECT_ROOT"

# Get current info
CURRENT_DATE=$(date '+%Y-%m-%d %H:%M')
CURRENT_MACHINE=$(uname -n)
CURRENT_OS="$(uname -s) $(uname -m)"
CURRENT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

echo -e "${GREEN}📅 Date:${NC} $CURRENT_DATE"
echo -e "${GREEN}💻 Machine:${NC} $CURRENT_MACHINE ($CURRENT_OS)"
echo -e "${GREEN}🔀 Branch:${NC} $CURRENT_BRANCH"
echo -e "${GREEN}📦 Commit:${NC} $CURRENT_COMMIT"
echo ""

# Prompt for session summary
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📝 SESSION SUMMARY${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check for uncommitted changes
CHANGED_FILES=$(git status --porcelain | wc -l | tr -d ' ')
if [ "$CHANGED_FILES" -gt 0 ]; then
    echo -e "${YELLOW}📁 Changed files ($CHANGED_FILES):${NC}"
    git status --porcelain | head -20
    echo ""
fi

# Get session summary from user or argument
if [ -n "$1" ]; then
    SESSION_SUMMARY="$1"
else
    echo -e "${YELLOW}Enter session summary (what was done this session):${NC}"
    read -r SESSION_SUMMARY
fi

if [ -z "$SESSION_SUMMARY" ]; then
    SESSION_SUMMARY="Session update"
fi

# Update CURRENT_STATE.md
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📄 UPDATING CURRENT_STATE.md${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Create updated CURRENT_STATE.md
cat > "$STATE_FILE" << EOF
# CURRENT_STATE.md - Session State Tracker

> **Last Updated:** $CURRENT_DATE (ICT)
> **Last Machine:** $CURRENT_MACHINE ($CURRENT_OS)
> **Last Commit:** $CURRENT_COMMIT
> **Branch:** $CURRENT_BRANCH

## Current Status: STABLE

$SESSION_SUMMARY

## Recent Session Summary

### Session: $CURRENT_DATE
- Machine: $CURRENT_MACHINE
- Summary: $SESSION_SUMMARY

## Changed Files This Session

\`\`\`
$(git status --porcelain 2>/dev/null || echo "No git changes")
\`\`\`

## Git Log (Recent)

\`\`\`
$(git log --oneline -5 2>/dev/null || echo "No git history")
\`\`\`

## Quick Resume Commands

\`\`\`bash
# Start server
./setup.sh --start

# Run tests
python tests/rpa_web_test.py

# Check status
./setup.sh --status
\`\`\`

## How to Continue

1. **Read this file** to understand current state
2. **Check git status** for any uncommitted work
3. **Run \`./setup.sh --status\`** to verify environment
4. **Ask user** what they want to work on next

---

## Session End Checklist

Before ending a session, ensure:
- [ ] All work is committed
- [ ] Tests pass (if applicable)
- [ ] This file is updated
- [ ] Changes are pushed to Git
EOF

echo -e "${GREEN}✅ CURRENT_STATE.md updated${NC}"
echo ""

# Stage .claude changes
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📦 PREPARING GIT COMMIT${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Add .claude changes
git add "$CLAUDE_DIR/"

# Show what will be committed
echo -e "${GREEN}Files staged for commit:${NC}"
git diff --cached --name-only
echo ""

# Ask for confirmation
echo -e "${YELLOW}Do you want to commit and push? (y/n)${NC}"
read -r CONFIRM

if [ "$CONFIRM" = "y" ] || [ "$CONFIRM" = "Y" ]; then
    # Commit
    git commit -m "chore: Update .claude session state

Session: $CURRENT_DATE
Machine: $CURRENT_MACHINE
Summary: $SESSION_SUMMARY

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"

    echo ""
    echo -e "${GREEN}✅ Committed successfully${NC}"

    # Push
    echo ""
    echo -e "${CYAN}Pushing to remote...${NC}"
    git push origin "$CURRENT_BRANCH"

    echo ""
    echo -e "${GREEN}✅ Pushed successfully${NC}"
else
    echo -e "${YELLOW}⚠️ Commit cancelled. Changes are staged but not committed.${NC}"
    echo "Run 'git commit' manually when ready."
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Session state saved! Ready to continue on another machine.${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
