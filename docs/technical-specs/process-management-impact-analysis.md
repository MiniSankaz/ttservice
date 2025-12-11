# Process Management Fix - Impact Analysis

> **Date:** 2025-12-11
> **Related Spec:** process-management-fix.md

---

## 1. Impact Analysis Table

| Module / File | Change Type | Risk Level | Impact Description | Dependencies Affected |
|---------------|-------------|------------|-------------------|----------------------|
| **app/database.py** | MODIFY | 🟡 MEDIUM | เพิ่ม 3 columns + 4 functions ใหม่ | ไม่กระทบ existing code, backward compatible |
| **app/migrations/001_add_process_tracking.sql** | NEW | 🟢 LOW | Migration script ใหม่ | ต้อง run manual หรือสร้าง migration runner |
| **lib/process_manager.py** | NEW | 🟡 MEDIUM | Class ใหม่ สำหรับจัดการ subprocess | ต้องติดตั้ง psutil library |
| **lib/audio.py** | MODIFY | 🔴 HIGH | แก้ไข run_transcription() function | **CRITICAL PATH** - กระทบการถอดเสียงทั้งหมด |
| **web_app.py** | MODIFY | 🔴 HIGH | แก้ไข 2 functions: show_transcribe_page(), show_job_details() | **CRITICAL PATH** - กระทบ UI flow |
| **scripts/transcribe_pipeline.py** | NO CHANGE | 🟢 LOW | ไม่ต้องแก้ไข | Output redirect เกิดที่ lib/audio.py |
| **app/services/mlx_pipeline/** | NO CHANGE | 🟢 LOW | ไม่ต้องแก้ไข | Process tracking เกิดที่ parent level |
| **tests/rpa_web_test.py** | MODIFY | 🟡 MEDIUM | เพิ่ม 2 test cases ใหม่ | Test 30, 31 |
| **requirements.txt** | MODIFY | 🟢 LOW | เพิ่ม psutil>=5.9.0 | ต้อง pip install |

---

## 2. Detailed Module Impact

### 🔴 HIGH RISK: lib/audio.py

**Current Code:**
```python
def run_transcription(...):
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, ...)
    for line in process.stdout:
        logs.append(line)
        if progress_callback:
            progress_callback(line)
    process.wait()
    return {'success': ..., 'logs': logs}
```

**Changes Required:**
1. เพิ่ม parameter: `job_id: Optional[int] = None`
2. เปลี่ยน stdout redirect ไปที่ log file
3. Register process กับ ProcessManager
4. Start monitoring thread
5. Stream logs จาก file แทน stdout

**Risk:**
- ถ้าเขียนผิด → ทุก transcription จะพัง
- ถ้า progress_callback ไม่ทำงาน → UI ไม่ update
- ถ้า log file เขียนไม่ได้ → process fail

**Mitigation:**
- Test thoroughly ก่อน deploy
- เก็บ original code ไว้เป็น fallback
- เพิ่ม error handling ทุกจุด
- Test กับหลาย audio files

**Testing Required:**
```bash
# Test 1: Normal transcription
python -c "from lib.audio import run_transcription; ..."

# Test 2: With job_id
python -c "from lib.audio import run_transcription; result = run_transcription(..., job_id=1); ..."

# Test 3: Without job_id (backward compatible)
python -c "from lib.audio import run_transcription; result = run_transcription(...); ..."
```

---

### 🔴 HIGH RISK: web_app.py

**Functions Affected:**
1. `show_transcribe_page()` - เพิ่มการส่ง job_id
2. `show_job_details()` - เพิ่ม live log viewer

**Changes Required in show_transcribe_page():**
```python
# เพิ่มการสร้าง job_id ก่อน run
job_id = create_job(...)

# ส่ง job_id ไปยัง run_transcription
result = run_transcription(..., job_id=job_id)
```

**Changes Required in show_job_details():**
```python
# เพิ่ม live log viewer สำหรับ processing jobs
if job['status'] == 'processing':
    pm = ProcessManager()
    status = pm.get_process_status(job_id)
    logs = pm.get_logs(job_id, lines=50)
    st.code('\n'.join(logs))
    # Auto-refresh
    time.sleep(5)
    st.rerun()
```

**Risk:**
- UI freeze ถ้า auto-refresh loop ผิดพลาด
- Streamlit rerun อาจทำให้ UI กระตุก
- Process metrics อาจใช้ CPU สูง

**Mitigation:**
- Test auto-refresh loop
- เพิ่ม "Stop Auto-refresh" button
- Cache process metrics
- Limit refresh rate

**Testing Required:**
- Test UI flow: Upload → Transcribe → Navigate → History → Monitor
- Test auto-refresh: ไม่ freeze, ไม่กระตุก
- Test stop button: kill process ได้จริง
- Test multiple tabs: ไม่ conflict

---

### 🟡 MEDIUM RISK: app/database.py

**Changes Required:**
```python
# 1. Add migration
ALTER TABLE transcription_jobs ADD COLUMN process_id INTEGER;
ALTER TABLE transcription_jobs ADD COLUMN log_file_path TEXT;
ALTER TABLE transcription_jobs ADD COLUMN last_heartbeat TIMESTAMP;

# 2. Add functions
def register_process(job_id, process_id, log_file_path):
    ...

def update_heartbeat(job_id):
    ...

def get_active_jobs():
    ...

def get_orphaned_jobs(timeout_seconds):
    ...
```

**Risk:**
- Migration fail → database unusable
- Existing data loss (ถ้าทำผิด)
- Index performance issues

**Mitigation:**
- **BACKUP DATABASE ก่อน migration**
- Test migration บน dev database ก่อน
- เขียน rollback script
- ทดสอบ performance ของ indexes

**Migration Steps:**
```bash
# 1. Backup
cp data/transcriptor.db data/transcriptor.db.backup

# 2. Run migration
sqlite3 data/transcriptor.db < app/migrations/001_add_process_tracking.sql

# 3. Verify
sqlite3 data/transcriptor.db ".schema transcription_jobs"

# 4. Test
python -c "from app.database import get_active_jobs; print(get_active_jobs())"
```

---

### 🟡 MEDIUM RISK: lib/process_manager.py (NEW)

**Changes Required:**
- สร้างไฟล์ใหม่
- Implement 15+ methods
- ทดสอบทุก method

**Risk:**
- Bug ใน ProcessManager → process leak
- Thread safety issues
- Resource exhaustion

**Mitigation:**
- Write comprehensive unit tests
- Use threading.Lock() everywhere
- Test with concurrent jobs
- Profile memory/CPU usage

**Testing Required:**
```python
# Unit tests
test_register_process()
test_is_process_running()
test_kill_process()
test_kill_process_tree()
test_get_logs()
test_cleanup_orphaned()

# Integration tests
test_full_transcription_with_tracking()
test_concurrent_jobs()
test_orphan_cleanup_while_processing()
```

---

### 🟡 MEDIUM RISK: tests/rpa_web_test.py

**Changes Required:**
- เพิ่ม test_30_monitor_processing_job
- เพิ่ม test_31_cleanup_orphaned_jobs

**Risk:**
- Test flakiness (timing issues)
- Test dependencies on server state

**Mitigation:**
- Use explicit waits
- Clean up test data after each test
- Mock external dependencies

---

## 3. Critical Path Analysis

### Critical Path 1: Transcription Flow
```
User uploads → create_job() → run_transcription(job_id) → ProcessManager.register()
                                       ↓
                              subprocess.Popen() → PID
                                       ↓
                            ProcessManager.start_monitoring()
                                       ↓
                             Update heartbeat every 5s
                                       ↓
                          Process completes → cleanup
```

**Bottlenecks:**
- ❌ ถ้า register_process() fail → PID ไม่ถูกบันทึก
- ❌ ถ้า monitoring thread crash → heartbeat หยุด
- ❌ ถ้า cleanup ไม่ทำงาน → orphaned processes

**Mitigation:**
- Wrap ทุกอย่างใน try-except
- Log ทุก error
- Implement health check

---

### Critical Path 2: Live Monitoring Flow
```
User → History → View Job (processing) → ProcessManager.get_process_status()
                                                 ↓
                                    Check PID with psutil
                                                 ↓
                               ProcessManager.get_logs(50 lines)
                                                 ↓
                                    st.code() display
                                                 ↓
                            Auto-refresh every 5s (st.rerun())
```

**Bottlenecks:**
- ❌ ถ้า log file ใหญ่ → slow read
- ❌ ถ้า refresh loop ติด → UI freeze
- ❌ ถ้า process check slow → delay

**Mitigation:**
- Tail only last 50 lines (fast)
- Add timeout to psutil calls
- Add "Stop Auto-refresh" button

---

## 4. Dependency Graph

```
web_app.py
    ↓ imports
lib/audio.py
    ↓ imports
lib/process_manager.py
    ↓ imports
app/database.py
    ↓ queries
transcription_jobs table (with new columns)
```

**External Dependencies:**
- psutil (NEW) - ต้อง `pip install psutil`
- sqlite3 (existing)
- subprocess (existing)
- threading (existing)

**Version Requirements:**
```
psutil>=5.9.0  # Stable release
Python>=3.10   # Already required
```

---

## 5. Performance Impact

### Memory Usage
| Component | Before | After | Delta |
|-----------|--------|-------|-------|
| ProcessManager | 0 MB | ~5 MB | +5 MB |
| Monitoring threads | 0 MB | ~1 MB/job | +N MB |
| Log files | 0 MB | ~10 MB/job | +10N MB |
| Database | ~1 MB | ~1.5 MB | +0.5 MB |
| **Total per job** | - | ~16 MB | +16 MB |

**Impact:** NEGLIGIBLE (16 MB per job vs 1-2 GB for process itself)

---

### CPU Usage
| Component | Before | After | Delta |
|-----------|--------|-------|-------|
| Heartbeat updates | 0% | <0.1% | +0.1% |
| Process checks | 0% | <0.1% | +0.1% |
| Log reading | 0% | <0.5% | +0.5% |
| **Total** | - | <1% | +<1% |

**Impact:** NEGLIGIBLE

---

### Database Performance
| Query | Frequency | Time | Impact |
|-------|-----------|------|--------|
| UPDATE heartbeat | Every 5s per job | <1ms | LOW |
| SELECT active_jobs | On page load | <5ms | LOW |
| SELECT orphaned | Every 10min | <10ms | LOW |

**Impact:** NEGLIGIBLE (all queries indexed)

---

## 6. Rollback Strategy

### If Critical Bug Found:

#### Option A: Feature Flag Disable
```python
# lib/audio.py
USE_PROCESS_TRACKING = False  # Rollback switch

def run_transcription(..., job_id=None):
    if USE_PROCESS_TRACKING and job_id:
        # New code
    else:
        # Original code (fallback)
```

**Time to Rollback:** 5 minutes (code change + restart)

---

#### Option B: Database Rollback
```bash
# Stop service
./setup.sh --stop

# Restore backup
cp data/transcriptor.db.backup data/transcriptor.db

# Remove new columns
sqlite3 data/transcriptor.db "ALTER TABLE transcription_jobs DROP COLUMN process_id"

# Restart
./setup.sh --start
```

**Time to Rollback:** 10 minutes

---

#### Option C: Git Revert
```bash
git revert <commit-hash>
git push
./setup.sh --restart
```

**Time to Rollback:** 15 minutes

---

## 7. Validation Checklist

### Pre-Deployment (ต้องผ่านทั้งหมด):
- [ ] Database migration tested on dev DB
- [ ] Database backup created
- [ ] Unit tests pass (lib/process_manager.py)
- [ ] Integration tests pass
- [ ] RPA tests pass (including new tests 30, 31)
- [ ] Manual testing: Upload → Transcribe → Monitor → Kill
- [ ] Manual testing: Orphaned process cleanup
- [ ] Performance testing: 3 concurrent jobs
- [ ] Memory leak testing: Run 10 jobs, check memory
- [ ] Log file rotation working
- [ ] Rollback procedure documented and tested

### Post-Deployment (ต้องตรวจสอบ):
- [ ] No orphaned processes after 1 hour
- [ ] All new jobs have PID registered
- [ ] Live log viewer working in History
- [ ] Stop button kills process successfully
- [ ] Auto-refresh not freezing UI
- [ ] Database size not growing abnormally
- [ ] Log files being cleaned up
- [ ] Error logs clean (no new errors)

---

## 8. Monitoring Plan

### Metrics to Track (First 24 Hours):
```python
{
    'total_jobs': 100,
    'jobs_with_pid': 100,          # Should be 100%
    'orphaned_cleaned': 0,          # Should be 0
    'active_processes': 2,
    'stuck_processes': 0,           # Should be 0
    'avg_heartbeat_delay': 5.1,     # Should be ~5s
    'log_files_count': 50,
    'log_files_size_mb': 500,
    'errors_count': 0               # Should be 0
}
```

### Alerts to Set:
1. **Critical:** orphaned_cleaned > 0 (investigate why)
2. **Warning:** stuck_processes > 0
3. **Warning:** log_files_size_mb > 10GB
4. **Info:** jobs_with_pid < 100% (tracking not working)

---

## 9. Documentation Updates Required

### Files to Update:
1. `.claude/KNOWN_ISSUES.md` - Remove process leak issue
2. `.claude/CURRENT_STATE.md` - Add "Process Management Implemented"
3. `.claude/DECISIONS.md` - Document why ProcessManager approach chosen
4. `CLAUDE.md` - Add ProcessManager to architecture diagram
5. `README.md` - Update features list
6. `USAGE.md` - Add "Monitoring Running Jobs" section

### New Documents to Create:
1. `docs/process-management-guide.md` - User guide
2. `docs/process-management-troubleshooting.md` - Troubleshooting
3. `app/migrations/README.md` - Migration guide

---

## 10. Timeline Estimate

| Phase | Tasks | Estimated Time | Risk Buffer | Total |
|-------|-------|----------------|-------------|-------|
| Phase 1 | Database Schema | 1-2 hours | +1 hour | 3 hours |
| Phase 2 | ProcessManager Class | 3-4 hours | +2 hours | 6 hours |
| Phase 3 | lib/audio.py Integration | 2 hours | +1 hour | 3 hours |
| Phase 4 | Web UI Integration | 3-4 hours | +2 hours | 6 hours |
| Phase 5 | Testing & Validation | 2-3 hours | +1 hour | 4 hours |
| Phase 6 | Documentation | 1 hour | +0.5 hour | 1.5 hours |
| **TOTAL** | | **12-16 hours** | **+7.5 hours** | **23.5 hours** |

**Realistic Timeline:** 3 working days (8 hours/day)

**Critical Path:** Phase 2 → Phase 3 → Phase 4 → Phase 5

**Parallel Work Possible:**
- Phase 1 และ Documentation (Phase 6) ทำพร้อมกันได้
- Unit tests เขียนไปพร้อม implementation (TDD approach)

---

## 11. Success Metrics

### After 1 Week:
- [ ] 0 orphaned processes detected
- [ ] 100% of jobs have PID tracking
- [ ] 0 memory leaks reported
- [ ] 0 critical bugs reported
- [ ] Live monitoring used in >50% of processing jobs

### After 1 Month:
- [ ] No process-related issues in KNOWN_ISSUES.md
- [ ] ProcessManager stable and tested
- [ ] Feature accepted by users
- [ ] Ready for production use

---

## 12. Risk Summary

| Risk Category | Level | Impact | Mitigation Status |
|--------------|-------|---------|-------------------|
| Process Leak | 🔴 HIGH | Memory exhaustion | ✅ Multi-level kill + health check |
| Database Corruption | 🔴 HIGH | Data loss | ✅ Backup + WAL mode + rollback |
| UI Freeze | 🟡 MEDIUM | Poor UX | ✅ Stop button + optimized refresh |
| Performance Degradation | 🟢 LOW | Slow app | ✅ Indexed queries + minimal overhead |
| Log File Growth | 🟡 MEDIUM | Disk full | ✅ Rotation + auto-cleanup |
| Race Conditions | 🟡 MEDIUM | Data inconsistency | ✅ Thread locks + atomic ops |

**Overall Risk Level:** 🟡 MEDIUM (with mitigations in place)

---

**Document Status:** Final
**Approved for Implementation:** Pending development-planner review

---

*Generated by system-analyst agent*
*TTService v1.0.0*
