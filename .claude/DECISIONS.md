# DECISIONS.md - Technical Decision Log

> This file records important technical decisions and their rationale.
> Useful for understanding "why" something was done a certain way.

---

## Decision Log

### DEC-001: Hybrid Multi-Process Architecture
**Date:** 2025-12-08
**Context:** Initial ThreadPool with 24 workers had lock contention issues (93% success rate)
**Decision:** Use 2 processes with 8 workers each
**Rationale:**
- Separate Python processes avoid GIL bottleneck
- Smaller thread pools (8 vs 24) reduce lock contention
- Each process has its own MLX model instance
- Result: 100% success rate, same speed (3.2x realtime)
**Trade-off:** Uses more memory (~1-2GB vs ~0.5GB)

---

### DEC-002: Support Both .npz and .safetensors
**Date:** 2025-12-09
**Context:** Thonburian model uses safetensors format, not npz
**Decision:** Check for both formats in model detection
**Rationale:**
- Older MLX models use weights.npz
- Newer models (including fine-tuned Thai) use weights.safetensors
- Both are valid MLX weight formats
**Implementation:** `lib/models.py` checks safetensors first, falls back to npz

---

### DEC-003: Dynamic Path Configuration
**Date:** 2025-12-09
**Context:** Project needs to be portable across different machines
**Decision:** All paths resolved from `Path(__file__).parent`
**Rationale:**
- No hardcoded absolute paths
- Works when cloned to any location
- Environment variables for override if needed
**Implementation:** `lib/config.py` with PROJECT_ROOT as base

---

### DEC-004: Modular lib/ Structure
**Date:** 2025-12-09
**Context:** web_app.py was growing too large (1500+ lines)
**Decision:** Extract reusable code to lib/ modules
**Rationale:**
- Separation of concerns
- Easier testing and maintenance
- Clear dependency documentation
- Reusable across CLI and Web interfaces
**Structure:**
```
lib/
├── config.py       # Configuration (no deps)
├── system.py       # System utils (deps: config)
├── audio.py        # Audio processing (deps: config)
├── models.py       # Model management (deps: config)
├── ui_components.py # UI helpers (deps: config)
└── pages/          # Page-specific modules
```

---

### DEC-005: Smart Chunking with Overlap
**Date:** 2025-12-08
**Context:** Splitting audio at fixed points cuts words
**Decision:** 20s chunks with 3s overlap
**Rationale:**
- 20s is optimal for Whisper context window
- 3s overlap ensures words aren't cut mid-utterance
- Overlap is deduplicated in post-processing
**Trade-off:** Slightly more processing, but much better accuracy

---

### DEC-006: SQLite for Local Storage
**Date:** 2025-12-08
**Context:** Need persistent history without external database
**Decision:** Use SQLite with file-based storage
**Rationale:**
- No server required
- Portable with the project
- Sufficient for single-user local application
- Easy backup (just copy the file)
**Location:** `data/transcriptor.db`

---

### DEC-007: Selenium RPA for Testing
**Date:** 2025-12-09
**Context:** Need to test Streamlit UI automatically
**Decision:** Use Selenium WebDriver with Chrome
**Rationale:**
- Streamlit doesn't have built-in test framework
- Selenium can interact with dynamic web elements
- Screenshots on failure for debugging
- Can run headless in CI
**Coverage:** 29 tests covering all major features

---

### DEC-008: .claude/ Resume System
**Date:** 2025-12-09
**Context:** Need to continue work across machines/sessions
**Decision:** Create .claude/ directory with context files
**Rationale:**
- Git-tracked for cross-machine sync
- Structured files for different purposes
- Easy to read and update
- Works with any Claude Code instance
**Structure:**
- PROJECT_CONTEXT.md: Static knowledge
- CURRENT_STATE.md: Dynamic state
- DECISIONS.md: This file

---

### DEC-009: Centralized Process Manager
**Date:** 2025-12-11
**Context:** Need robust process lifecycle management for transcription jobs
**Decision:** Create `lib/process_manager.py` as singleton with heartbeat monitoring
**Rationale:**
- Centralized subprocess tracking by job_id
- Heartbeat thread detects orphaned processes (every 5s)
- Log capture (file + in-memory) for debugging
- Graceful shutdown (SIGTERM → SIGKILL fallback)
- Database integration for persistence
**Implementation:**
- Singleton pattern for global instance
- Thread-safe operations with locks
- Logs stored in `logs/jobs/job_{id}_{timestamp}.log`
- Database columns: pid, heartbeat, log_file
**Trade-off:** Slightly more complex than simple subprocess.run(), but much more reliable

---

### DEC-010: Real Claude Code CLI Integration
**Date:** 2025-12-11
**Context:** Claude Terminal used keyword matching (fake responses)
**Decision:** Integrate real Claude Code CLI via `subprocess.Popen(['claude', ...])`
**Rationale:**
- Actual AI assistance instead of hardcoded responses
- Context-aware command execution
- Live streaming output in web UI
- Consistent with Claude Code's design
**Implementation:** `lib/pages/settings.py` - Claude Terminal tab
**Trade-off:** Requires Claude CLI installed, but provides real value

---

### DEC-011: Database Schema Extension for Process Tracking
**Date:** 2025-12-11
**Context:** Need to track process state across restarts
**Decision:** Add pid, heartbeat, log_file columns to transcription_jobs
**Rationale:**
- PID tracking enables kill/stop operations
- Heartbeat detects stale/orphaned jobs
- Log file path for retrieval after completion
- Auto-migration for existing databases
**Implementation:**
- `ALTER TABLE` with try/except for backwards compatibility
- New functions: update_heartbeat, get_orphaned_jobs, cancel_job
- Indexes on pid and heartbeat for fast queries
**Trade-off:** None - backwards compatible migration

---

### DEC-012: Job Cancellation Feature
**Date:** 2025-12-11
**Context:** Users need ability to stop long-running transcriptions
**Decision:** Add Stop/Cancel button in History UI with ProcessManager integration
**Rationale:**
- User control over resource usage
- Graceful termination prevents data corruption
- Updates job status to 'cancelled' in database
- Cleans up process from tracking
**Implementation:**
- Button shows for 'processing' jobs only
- Calls `ProcessManager.stop_process(job_id)`
- UI updates via rerun after cancellation
**Trade-off:** None - essential feature

---

## Decision Template

```markdown
### DEC-XXX: [Title]
**Date:** YYYY-MM-DD
**Context:** [What problem or situation prompted this decision]
**Decision:** [What was decided]
**Rationale:** [Why this decision was made]
**Trade-off:** [Any downsides or alternatives considered]
**Implementation:** [Where/how this is implemented]
```
