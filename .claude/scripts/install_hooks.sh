#!/bin/bash
# =============================================================================
# install_hooks.sh - Install Git Hooks for Auto Session Save
# =============================================================================
# This script installs git hooks that automatically save session state
# before pushing to remote.
#
# Usage: ./.claude/scripts/install_hooks.sh
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
GIT_HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           🔧 INSTALL GIT HOOKS                                 ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .git exists
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${YELLOW}⚠️  Not a git repository!${NC}"
    exit 1
fi

# Create hooks directory if not exists
mkdir -p "$GIT_HOOKS_DIR"

# Create pre-push hook
echo -e "${GREEN}📝 Creating pre-push hook...${NC}"

cat > "$GIT_HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# =============================================================================
# pre-push hook - Auto-save Claude session state before push
# =============================================================================

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get project root
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"
STATE_FILE="$CLAUDE_DIR/CURRENT_STATE.md"

# Check if .claude directory exists
if [ ! -d "$CLAUDE_DIR" ]; then
    exit 0  # Skip if no .claude directory
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🤖 Auto-saving Claude session state...${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Get current info
CURRENT_DATE=$(date '+%Y-%m-%d %H:%M')
CURRENT_MACHINE=$(uname -n)
CURRENT_OS="$(uname -s) $(uname -m)"
CURRENT_COMMIT=$(git rev-parse --short HEAD)
CURRENT_BRANCH=$(git branch --show-current)

# Update CURRENT_STATE.md with minimal info
cat > "$STATE_FILE" << INNEREOF
# CURRENT_STATE.md - Session State Tracker

> **Last Updated:** $CURRENT_DATE (ICT)
> **Last Machine:** $CURRENT_MACHINE ($CURRENT_OS)
> **Last Commit:** $CURRENT_COMMIT
> **Branch:** $CURRENT_BRANCH

## Current Status: STABLE

Auto-saved before git push.

## Git Log (Recent)

\`\`\`
$(git log --oneline -5)
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
2. **Read .claude/PROJECT_CONTEXT.md** for project architecture
3. **Run \`./setup.sh --status\`** to verify environment
4. **Ask user** what they want to work on next

---

*This file was auto-updated by pre-push hook*
INNEREOF

# Stage and amend the commit with session state
git add "$CLAUDE_DIR/CURRENT_STATE.md"

# Check if there are changes to commit
if ! git diff --cached --quiet; then
    git commit --amend --no-edit
    echo -e "${GREEN}✅ Session state saved and committed${NC}"
fi

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

exit 0
EOF

chmod +x "$GIT_HOOKS_DIR/pre-push"

echo -e "${GREEN}✅ pre-push hook installed${NC}"
echo ""

# Create post-checkout hook for resume reminder
echo -e "${GREEN}📝 Creating post-checkout hook...${NC}"

cat > "$GIT_HOOKS_DIR/post-checkout" << 'EOF'
#!/bin/bash
# =============================================================================
# post-checkout hook - Remind to resume Claude session
# =============================================================================

# Only run on branch checkout (not file checkout)
if [ "$3" != "1" ]; then
    exit 0
fi

# Colors
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get project root
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"

# Check if .claude directory exists
if [ ! -d "$CLAUDE_DIR" ]; then
    exit 0
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🤖 Claude Code Resume System${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}To resume Claude conversation:${NC}"
echo "  1. Run: ./.claude/scripts/resume.sh"
echo "  2. Start Claude Code: claude"
echo "  3. Say: \"อ่าน .claude/ แล้วทำงานต่อ\""
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

exit 0
EOF

chmod +x "$GIT_HOOKS_DIR/post-checkout"

echo -e "${GREEN}✅ post-checkout hook installed${NC}"
echo ""

echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ All hooks installed successfully!${NC}"
echo ""
echo -e "Hooks installed:"
echo -e "  - ${GREEN}pre-push${NC}: Auto-saves session state before push"
echo -e "  - ${GREEN}post-checkout${NC}: Shows resume reminder on branch switch"
echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
