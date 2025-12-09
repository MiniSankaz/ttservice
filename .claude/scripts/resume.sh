#!/bin/bash
# =============================================================================
# resume.sh - Resume Claude Code Conversation
# =============================================================================
# This script helps resume Claude Code conversations from any machine.
# It displays the project context and current state for quick onboarding.
#
# Usage: ./.claude/scripts/resume.sh
# =============================================================================

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CLAUDE_DIR="$PROJECT_ROOT/.claude"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           🤖 CLAUDE CODE CONVERSATION RESUME                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if .claude directory exists
if [ ! -d "$CLAUDE_DIR" ]; then
    echo -e "${YELLOW}⚠️  .claude/ directory not found!${NC}"
    echo "Please ensure you're in the correct project directory."
    exit 1
fi

# Display project info
echo -e "${GREEN}📁 Project Root:${NC} $PROJECT_ROOT"
echo -e "${GREEN}📅 Current Date:${NC} $(date '+%Y-%m-%d %H:%M:%S')"
echo -e "${GREEN}💻 Machine:${NC} $(uname -n) ($(uname -s) $(uname -m))"
echo ""

# Display current state summary
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📊 CURRENT STATE SUMMARY${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ -f "$CLAUDE_DIR/CURRENT_STATE.md" ]; then
    # Extract key info from CURRENT_STATE.md
    echo ""
    head -20 "$CLAUDE_DIR/CURRENT_STATE.md" | tail -15
    echo ""
    echo -e "${YELLOW}📄 Full state: .claude/CURRENT_STATE.md${NC}"
else
    echo -e "${YELLOW}⚠️  CURRENT_STATE.md not found${NC}"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}📚 AVAILABLE CONTEXT FILES${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# List context files
for file in "$CLAUDE_DIR"/*.md; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        lines=$(wc -l < "$file" | tr -d ' ')
        echo -e "  📄 ${GREEN}$filename${NC} ($lines lines)"
    fi
done

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🚀 QUICK COMMANDS${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${GREEN}Start Claude Code:${NC}"
echo "    cd $PROJECT_ROOT && claude"
echo ""
echo -e "  ${GREEN}Resume prompt (copy this to Claude):${NC}"
echo -e "    ${YELLOW}\"อ่าน .claude/ แล้วทำงานต่อ\"${NC}"
echo ""
echo -e "  ${GREEN}Or in English:${NC}"
echo -e "    ${YELLOW}\"Read .claude/ directory and resume work\"${NC}"
echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check git status
echo -e "${CYAN}📦 GIT STATUS${NC}"
cd "$PROJECT_ROOT"
if git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    BRANCH=$(git branch --show-current)
    COMMIT=$(git rev-parse --short HEAD)
    echo -e "  Branch: ${GREEN}$BRANCH${NC}"
    echo -e "  Commit: ${GREEN}$COMMIT${NC}"

    # Check for uncommitted changes
    if [ -n "$(git status --porcelain)" ]; then
        echo -e "  Status: ${YELLOW}Has uncommitted changes${NC}"
    else
        echo -e "  Status: ${GREEN}Clean${NC}"
    fi
else
    echo -e "  ${YELLOW}Not a git repository${NC}"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Ready to resume! Start Claude Code and use the resume prompt.${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
