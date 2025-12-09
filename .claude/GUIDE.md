# 📖 คู่มือ Resume Conversation System

## สารบัญ
1. [แนวคิดและหลักการ](#1-แนวคิดและหลักการ)
2. [การติดตั้งครั้งแรก](#2-การติดตั้งครั้งแรก)
3. [การใช้งานประจำวัน](#3-การใช้งานประจำวัน)
4. [Scripts Reference](#4-scripts-reference)
5. [โครงสร้างไฟล์](#5-โครงสร้างไฟล์)
6. [Best Practices](#6-best-practices)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. แนวคิดและหลักการ

### ทำไมต้องมี Resume System?

เมื่อใช้ Claude Code ในการพัฒนา project ข้ามหลายเครื่องหรือหลาย session:
- Claude ไม่มี memory ระหว่าง session
- ต้องอธิบายซ้ำทุกครั้งว่าทำอะไรไปแล้ว
- เสียเวลาในการ onboard Claude ใหม่

### วิธีแก้ปัญหา

```
┌─────────────────────────────────────────────────────────────┐
│  .claude/ Directory (Git-tracked)                           │
│  ═══════════════════════════════════════════════════════════│
│                                                             │
│  📄 PROJECT_CONTEXT.md   → ความรู้ถาวร (แก้ไขน้อย)          │
│  📄 CURRENT_STATE.md     → สถานะปัจจุบัน (auto-update)      │
│  📄 DECISIONS.md         → บันทึกการตัดสินใจ                │
│  📄 KNOWN_ISSUES.md      → ปัญหาที่รู้จัก                    │
│                                                             │
│  📁 scripts/                                                │
│     ├── resume.sh        → แสดงสถานะเพื่อ resume            │
│     ├── save_session.sh  → บันทึก session                   │
│     └── install_hooks.sh → ติดตั้ง git hooks                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ทุกครั้งที่ push → auto-save state
              ทุกครั้งที่ clone → พร้อม resume ทันที
```

---

## 2. การติดตั้งครั้งแรก

### 2.1 Clone Repository

```bash
git clone https://github.com/MiniSankaz/ttservice.git
cd transcriptor-pipeline-pilot
```

### 2.2 ติดตั้ง Git Hooks

```bash
./.claude/scripts/install_hooks.sh
```

**Output ที่คาดหวัง:**
```
╔════════════════════════════════════════════════════════════════╗
║           🔧 INSTALL GIT HOOKS                                 ║
╚════════════════════════════════════════════════════════════════╝

📝 Creating pre-push hook...
✅ pre-push hook installed

📝 Creating post-checkout hook...
✅ post-checkout hook installed

════════════════════════════════════════════════════════════════
✅ All hooks installed successfully!
```

### 2.3 ดูสถานะ Project

```bash
./.claude/scripts/resume.sh
```

---

## 3. การใช้งานประจำวัน

### 3.1 เริ่มทำงาน (Resume Session)

```bash
# 1. ดู state ปัจจุบัน
./.claude/scripts/resume.sh

# 2. เปิด Claude Code
claude

# 3. พิมพ์ prompt นี้:
"อ่าน .claude/ แล้วทำงานต่อ"

# หรือภาษาอังกฤษ:
"Read .claude/ directory and resume work"
```

### 3.2 ระหว่างทำงาน

ทำงานตามปกติกับ Claude Code ไม่ต้องทำอะไรเพิ่ม

### 3.3 จบ Session

**วิธี 1: Auto-save (แนะนำ)**
```bash
# แค่ push ตามปกติ - hook จะ save state ให้อัตโนมัติ
git add .
git commit -m "your commit message"
git push
```

**วิธี 2: Manual save**
```bash
# บันทึกพร้อม summary
./.claude/scripts/save_session.sh "เพิ่ม feature X และแก้ bug Y"
```

### 3.4 Workflow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Machine A │     │  Git Remote │     │  Machine B  │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       │  ทำงานกับ Claude  │                   │
       │         │         │                   │
       │         ▼         │                   │
       │  git push ────────┼──────────────────►│
       │  (auto-save)      │                   │
       │                   │                   │  git pull
       │                   │                   │     │
       │                   │                   │     ▼
       │                   │                   │  resume.sh
       │                   │                   │     │
       │                   │                   │     ▼
       │                   │                   │  Start Claude
       │                   │                   │     │
       │                   │                   │     ▼
       │                   │                   │  "อ่าน .claude/..."
       │                   │                   │     │
       │                   │                   │     ▼
       │                   │                   │  ทำงานต่อ!
```

---

## 4. Scripts Reference

### 4.1 resume.sh

**Purpose:** แสดงสถานะ project สำหรับ resume session

```bash
./.claude/scripts/resume.sh
```

**แสดงข้อมูล:**
- Project root path
- Current date/machine
- CURRENT_STATE.md summary
- Available context files
- Git status
- Quick commands

### 4.2 save_session.sh

**Purpose:** บันทึก session state แบบ manual

```bash
# แบบ interactive
./.claude/scripts/save_session.sh

# แบบระบุ summary
./.claude/scripts/save_session.sh "สิ่งที่ทำใน session นี้"
```

**ขั้นตอน:**
1. แสดง changed files
2. รับ session summary
3. อัพเดต CURRENT_STATE.md
4. ถาม confirm ก่อน commit/push

### 4.3 install_hooks.sh

**Purpose:** ติดตั้ง git hooks สำหรับ auto-save

```bash
./.claude/scripts/install_hooks.sh
```

**Hooks ที่ติดตั้ง:**

| Hook | Trigger | Action |
|------|---------|--------|
| `pre-push` | ก่อน `git push` | Auto-save CURRENT_STATE.md |
| `post-checkout` | หลังเปลี่ยน branch | แสดง resume reminder |

---

## 5. โครงสร้างไฟล์

### 5.1 Context Files

```
.claude/
├── README.md              # คำอธิบาย .claude/ directory
├── GUIDE.md               # คู่มือนี้
├── PROJECT_CONTEXT.md     # ความรู้ถาวรของ project
├── CURRENT_STATE.md       # สถานะปัจจุบัน (auto-update)
├── DECISIONS.md           # บันทึกการตัดสินใจทางเทคนิค
├── KNOWN_ISSUES.md        # ปัญหาที่รู้จักและวิธีแก้
└── scripts/
    ├── resume.sh          # แสดงสถานะเพื่อ resume
    ├── save_session.sh    # บันทึก session
    └── install_hooks.sh   # ติดตั้ง git hooks
```

### 5.2 รายละเอียดแต่ละไฟล์

#### PROJECT_CONTEXT.md
- **เนื้อหา:** Architecture, module structure, design decisions
- **แก้ไข:** เมื่อมีการเปลี่ยนแปลง architecture ใหญ่
- **ใครแก้:** Developer/Claude เมื่อ refactor

#### CURRENT_STATE.md
- **เนื้อหา:** Last session info, pending tasks, recent changes
- **แก้ไข:** ทุกครั้งที่ push (auto by hook)
- **ใครแก้:** Git hook / save_session.sh

#### DECISIONS.md
- **เนื้อหา:** Technical decisions และเหตุผล
- **แก้ไข:** เมื่อตัดสินใจทางเทคนิคสำคัญ
- **ใครแก้:** Developer/Claude เมื่อตัดสินใจ

#### KNOWN_ISSUES.md
- **เนื้อหา:** Bugs, limitations, workarounds
- **แก้ไข:** เมื่อพบ/แก้ไข issues
- **ใครแก้:** Developer/Claude เมื่อพบปัญหา

---

## 6. Best Practices

### 6.1 สำหรับการใช้งาน

✅ **DO:**
- Run `install_hooks.sh` หลัง clone ทุกครั้ง
- ใช้ `resume.sh` ดู state ก่อนเริ่มงาน
- Let hooks handle auto-save (แค่ push ปกติ)
- อัพเดต DECISIONS.md เมื่อตัดสินใจสำคัญ

❌ **DON'T:**
- อย่าแก้ CURRENT_STATE.md manually (ปล่อยให้ hook จัดการ)
- อย่าลืม install hooks บนเครื่องใหม่
- อย่าลบ .claude/ directory

### 6.2 สำหรับ Claude Prompts

**เริ่ม session:**
```
"อ่าน .claude/ แล้วทำงานต่อ"
```

**จบ session:**
```
"อัพเดต .claude/ และ commit"
```

**ถามเกี่ยวกับ project:**
```
"ดู DECISIONS.md ว่าทำไมถึงใช้ hybrid architecture"
```

### 6.3 Template สำหรับ Decision Log

เมื่อต้องการเพิ่ม decision ใหม่:

```markdown
### DEC-XXX: [ชื่อ Decision]
**Date:** YYYY-MM-DD
**Context:** [สถานการณ์ที่ต้องตัดสินใจ]
**Decision:** [สิ่งที่ตัดสินใจ]
**Rationale:** [เหตุผล]
**Trade-off:** [ข้อเสียหรือ alternative ที่พิจารณา]
**Implementation:** [ไฟล์/code ที่เกี่ยวข้อง]
```

---

## 7. Troubleshooting

### 7.1 Hooks ไม่ทำงาน

**ปัญหา:** push แล้ว state ไม่ update

**แก้ไข:**
```bash
# ตรวจสอบ hooks
ls -la .git/hooks/

# ติดตั้งใหม่
./.claude/scripts/install_hooks.sh
```

### 7.2 resume.sh แสดง error

**ปัญหา:** "Not a git repository"

**แก้ไข:**
```bash
# ตรวจสอบว่าอยู่ใน project directory
pwd
ls -la .git/
```

### 7.3 Claude ไม่เข้าใจ context

**ปัญหา:** Claude ถามซ้ำเรื่องที่ควรรู้แล้ว

**แก้ไข:**
```
# ใช้ prompt ที่ชัดเจนกว่า:
"อ่าน .claude/PROJECT_CONTEXT.md และ .claude/CURRENT_STATE.md
แล้วสรุปให้ฟังว่า project นี้ทำอะไร และทำอะไรไปแล้วบ้าง"
```

### 7.4 Merge conflicts ใน CURRENT_STATE.md

**ปัญหา:** หลายคนแก้พร้อมกัน

**แก้ไข:**
```bash
# ใช้ version ล่าสุดจาก remote
git checkout --theirs .claude/CURRENT_STATE.md
git add .claude/CURRENT_STATE.md

# หรือ regenerate
./.claude/scripts/save_session.sh "Resolved merge conflict"
```

---

## Quick Reference Card

```
┌────────────────────────────────────────────────────────────┐
│  🤖 CLAUDE CODE RESUME SYSTEM - QUICK REFERENCE            │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  📥 SETUP (ครั้งเดียวหลัง clone):                          │
│     ./.claude/scripts/install_hooks.sh                     │
│                                                            │
│  ▶️  START SESSION:                                        │
│     ./.claude/scripts/resume.sh                            │
│     claude                                                 │
│     "อ่าน .claude/ แล้วทำงานต่อ"                           │
│                                                            │
│  ⏹️  END SESSION:                                          │
│     git push  (auto-save by hook)                          │
│     หรือ ./.claude/scripts/save_session.sh "summary"       │
│                                                            │
│  📂 FILES:                                                 │
│     PROJECT_CONTEXT.md  → Architecture (stable)            │
│     CURRENT_STATE.md    → Current state (auto-update)      │
│     DECISIONS.md        → Decision log                     │
│     KNOWN_ISSUES.md     → Bug tracking                     │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

*คู่มือนี้เป็นส่วนหนึ่งของ Transcriptor Pipeline Pilot project*
*Last updated: 2025-12-09*
