# Process Management Fix - Quick Reference

> **Quick Start Guide for Developers**
> ⚡ คู่มือฉบับย่อสำหรับ implement Process Management Fix

---

## 🎯 สิ่งที่จะได้หหลังจาก implement

✅ ติดตาม PID ของ subprocess ใน database
✅ Kill process เมื่อ user navigate ออก
✅ Monitor live logs ของ job ที่กำลัง processing
✅ Auto-cleanup orphaned processes
✅ ดู CPU/Memory usage ของ process

---

## 📋 Implementation Checklist

### Phase 1: Database (30 min)
```bash
# 1. Backup database
cp data/transcriptor.db data/transcriptor.db.backup

# 2. Run migration
sqlite3 data/transcriptor.db < app/migrations/001_add_process_tracking.sql

# 3. Verify
sqlite3 data/transcriptor.db ".schema transcription_jobs"
# Should see: process_id, log_file_path, last_heartbeat columns

# 4. Test
python -c "from app.database import get_active_jobs; print(get_active_jobs())"
```

---

### Phase 2: ProcessManager (2 hours)
```bash
# 1. Install dependency
pip install psutil

# 2. Create file
touch lib/process_manager.py

# 3. Copy implementation from spec (Section 4)

# 4. Test
python -c "
from lib.process_manager import ProcessManager
import subprocess
pm = ProcessManager()
proc = subprocess.Popen(['sleep', '5'])
info = pm.register_process(999, proc, ['sleep', '5'])
print(f'Registered: {info}')
print(f'Running: {pm.is_process_running(999)}')
pm.kill_process(999)
"
```

---

### Phase 3: lib/audio.py (1 hour)
```python
# Add to run_transcription() signature
def run_transcription(
    ...,
    job_id: Optional[int] = None  # ← ADD THIS
) -> Dict:

    # Add at start of function
    if job_id:
        from lib.process_manager import ProcessManager
        process_mgr = ProcessManager()
        log_path = process_mgr.log_dir / f"transcribe_job_{job_id}.log"
        log_file = open(log_path, 'w')
        stdout_target = log_file
    else:
        log_file = None
        stdout_target = subprocess.PIPE

    # Change subprocess.Popen
    process = subprocess.Popen(
        cmd,
        stdout=stdout_target,  # ← CHANGE THIS
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Register process
    if job_id:
        process_mgr.register_process(job_id, process, cmd)

    # ... rest of function
```

**Test:**
```bash
python -c "
from lib.audio import run_transcription
from app.database import create_job

job_id = create_job('test.mp3', '/tmp/test.mp3', 1.0, 'tiny', 1, 2)
result = run_transcription('/tmp/test.mp3', '/tmp/out.txt', 'tiny', 1, 2, job_id=job_id)
print(f'Success: {result[\"success\"]}')
"
```

---

### Phase 4: web_app.py (1.5 hours)

#### In show_transcribe_page():
```python
# BEFORE: result = run_transcription(...)

# ADD:
job_id = create_job(
    filename=uploaded_file.name,
    original_path=str(temp_input),
    duration_minutes=duration,
    model=model,
    processes=processes,
    workers=workers
)

# CHANGE:
result = run_transcription(
    str(temp_input),
    str(output_path),
    model,
    processes,
    workers,
    update_progress,
    chunk_duration,
    overlap_duration,
    job_id=job_id  # ← ADD THIS
)
```

#### In show_job_details():
```python
# ADD after existing job info display:

if job['status'] == 'processing':
    from lib.process_manager import ProcessManager
    pm = ProcessManager()

    st.markdown("### 📊 Live Logs")

    # Process status
    status = pm.get_process_status(job_id)

    if status['running']:
        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("CPU", f"{status['cpu_percent']:.1f}%")
        col2.metric("Memory", f"{status['memory_mb']:.0f} MB")
        col3.metric("Elapsed", f"{status['elapsed_seconds']/60:.1f} min")

        # Stop button
        if st.button("🛑 Stop Transcription"):
            pm.kill_process_tree(job_id)
            fail_job(job_id, "Stopped by user")
            st.success("Stopped!")
            time.sleep(1)
            st.rerun()

        # Logs
        logs = pm.get_logs(job_id, lines=50)
        st.code('\n'.join(logs), language='text')

        # Auto-refresh
        st.markdown("*Auto-refreshing...*")
        time.sleep(5)
        st.rerun()
    else:
        st.warning("Process not running")
```

---

### Phase 5: Testing (1 hour)
```bash
# Unit tests
python tests/unit/test_process_manager.py

# Integration test
python -c "
from lib.audio import run_transcription
from app.database import create_job, get_job
from lib.process_manager import ProcessManager

# Create and run job
job_id = create_job('test.mp3', '/tmp/test.mp3', 1.0, 'tiny', 1, 2)
result = run_transcription('/tmp/test.mp3', '/tmp/out.txt', 'tiny', 1, 2, job_id=job_id)

# Verify
job = get_job(job_id)
assert job['process_id'] is not None
assert job['log_file_path'] is not None

pm = ProcessManager()
log_path = pm.get_log_path(job_id)
assert log_path.exists()

print('✅ All checks passed!')
"

# RPA tests
python tests/rpa_web_test.py
```

---

## 🔑 Key Code Snippets

### 1. Register Process
```python
from lib.process_manager import ProcessManager

pm = ProcessManager()
info = pm.register_process(job_id, process, command)
# Returns: {'pid': 12345, 'log_path': '/tmp/...', 'registered': True}
```

### 2. Check Process Status
```python
status = pm.get_process_status(job_id)
# Returns: {
#   'running': True,
#   'pid': 12345,
#   'cpu_percent': 45.2,
#   'memory_mb': 1024.5,
#   'elapsed_seconds': 120.5
# }
```

### 3. Get Logs
```python
logs = pm.get_logs(job_id, lines=50)
# Returns: ['line1', 'line2', ...]
```

### 4. Kill Process
```python
pm.kill_process(job_id)  # Graceful (SIGTERM)
pm.kill_process_tree(job_id)  # Kill with children
```

### 5. Cleanup Orphaned
```python
pm.cleanup_orphaned_processes(timeout_seconds=300)
# Finds and kills processes with no heartbeat for 5+ minutes
```

---

## 🗂️ Database Functions

### Register Process
```python
from app.database import register_process

register_process(job_id, pid, log_file_path)
```

### Update Heartbeat
```python
from app.database import update_heartbeat

update_heartbeat(job_id)  # Call every 5 seconds
```

### Get Active Jobs
```python
from app.database import get_active_jobs

jobs = get_active_jobs()
# Returns: [{'id': 1, 'process_id': 12345, ...}, ...]
```

### Get Orphaned Jobs
```python
from app.database import get_orphaned_jobs

orphaned = get_orphaned_jobs(timeout_seconds=300)
# Returns jobs with no heartbeat for 5+ minutes
```

---

## 🧪 Testing Commands

### Quick Smoke Test
```bash
# 1. Start server
./setup.sh --start

# 2. Upload file and transcribe
# (Use UI)

# 3. Check database
sqlite3 data/transcriptor.db "SELECT id, filename, process_id, status FROM transcription_jobs ORDER BY id DESC LIMIT 5"

# 4. Check logs
ls -lh /tmp/transcribe_job_*.log

# 5. Check processes
ps aux | grep transcribe_pipeline
```

### Test Process Cleanup
```bash
# 1. Create fake orphaned job
python -c "
from app.database import create_job, register_process
from datetime import datetime, timedelta

job_id = create_job('fake.mp3', '/tmp/fake.mp3', 1.0, 'tiny', 1, 2)
register_process(job_id, 99999, '/tmp/fake.log')

# Set old heartbeat
from app.database import get_connection
with get_connection() as conn:
    old = datetime.now() - timedelta(minutes=10)
    conn.execute('UPDATE transcription_jobs SET last_heartbeat = ? WHERE id = ?', (old, job_id))
    conn.commit()

print(f'Created orphaned job: {job_id}')
"

# 2. Run cleanup
python -c "
from lib.process_manager import ProcessManager
pm = ProcessManager()
pm.cleanup_orphaned_processes(timeout_seconds=300)
"

# 3. Verify
sqlite3 data/transcriptor.db "SELECT id, status, error_message FROM transcription_jobs WHERE id = <job_id>"
# Should show status = 'failed', error_message = 'orphaned...'
```

---

## 📊 Monitoring Commands

### Check Active Processes
```python
from app.database import get_active_jobs
from lib.process_manager import ProcessManager

pm = ProcessManager()

for job in get_active_jobs():
    status = pm.get_process_status(job['id'])
    print(f"Job {job['id']}: PID={status['pid']}, Running={status['running']}, CPU={status['cpu_percent']}%")
```

### Check Log Files
```bash
# List all log files
ls -lh /tmp/transcribe_job_*.log

# Tail specific job
tail -f /tmp/transcribe_job_123.log

# Tail multiple jobs
tail -f /tmp/transcribe_job_*.log
```

### Check Database Stats
```sql
-- Active jobs
SELECT COUNT(*) FROM transcription_jobs WHERE status = 'processing';

-- Jobs with PID
SELECT COUNT(*) FROM transcription_jobs WHERE process_id IS NOT NULL;

-- Recent heartbeats
SELECT id, filename, last_heartbeat,
       datetime('now') - last_heartbeat as age_seconds
FROM transcription_jobs
WHERE status = 'processing'
ORDER BY last_heartbeat DESC;
```

---

## 🐛 Troubleshooting

### Problem: Process not registered
**Symptoms:** `process_id` is NULL in database

**Debug:**
```python
from app.database import get_job
job = get_job(job_id)
print(f"Process ID: {job['process_id']}")  # Should not be None
print(f"Log path: {job['log_file_path']}")  # Should exist
```

**Fix:**
- Check if `job_id` is passed to `run_transcription()`
- Check if ProcessManager import works
- Check logs for errors

---

### Problem: Orphaned processes not cleaned
**Symptoms:** Process still running after session ends

**Debug:**
```python
from app.database import get_orphaned_jobs
orphaned = get_orphaned_jobs(timeout_seconds=300)
print(f"Found {len(orphaned)} orphaned jobs")
for job in orphaned:
    print(f"  Job {job['id']}: PID={job['process_id']}, Last heartbeat={job['last_heartbeat']}")
```

**Fix:**
- Call `pm.cleanup_orphaned_processes()` manually
- Check if monitoring thread is running
- Reduce timeout (try 60 seconds)

---

### Problem: Logs not showing
**Symptoms:** Empty log in UI

**Debug:**
```python
from lib.process_manager import ProcessManager
from pathlib import Path

pm = ProcessManager()
log_path = pm.get_log_path(job_id)
print(f"Log path: {log_path}")
print(f"Exists: {log_path.exists()}")
if log_path.exists():
    print(f"Size: {log_path.stat().st_size} bytes")
    print(f"Content:\n{log_path.read_text()}")
```

**Fix:**
- Check if log file exists
- Check if subprocess writes to stdout
- Check file permissions

---

### Problem: UI freezes on auto-refresh
**Symptoms:** Streamlit stops responding

**Fix:**
- Add timeout to process checks
- Limit log lines (50 max)
- Add "Stop Auto-refresh" button
- Check for infinite loop

---

## 🚀 Performance Tips

### 1. Optimize Log Reading
```python
# Good: Read last N lines only
logs = pm.get_logs(job_id, lines=50)

# Bad: Read entire file
with open(log_path) as f:
    logs = f.readlines()  # Could be huge!
```

### 2. Cache Process Status
```python
# Good: Cache for 5 seconds
@st.cache_data(ttl=5)
def get_cached_status(job_id):
    return pm.get_process_status(job_id)

# Bad: Query every render
status = pm.get_process_status(job_id)  # Called 10x per second
```

### 3. Batch Heartbeat Updates
```python
# Good: Update every 5 seconds
time.sleep(5)
update_heartbeat(job_id)

# Bad: Update every second
time.sleep(1)
update_heartbeat(job_id)  # Too frequent!
```

---

## 📚 Reference Links

- **Full Spec:** `docs/technical-specs/process-management-fix.md`
- **Impact Analysis:** `docs/technical-specs/process-management-impact-analysis.md`
- **ProcessManager API:** Section 4 in full spec
- **Database Schema:** Section 3 in full spec
- **Testing Guide:** Section 11 in impact analysis

---

## 🆘 Emergency Rollback

### If Something Goes Wrong:

#### Quick Disable (5 minutes):
```python
# lib/audio.py - Line ~81
def run_transcription(..., job_id=None):
    USE_PROCESS_TRACKING = False  # ← ADD THIS LINE

    if USE_PROCESS_TRACKING and job_id:  # ← Will skip new code
        ...
```

#### Full Rollback (10 minutes):
```bash
# 1. Stop service
./setup.sh --stop

# 2. Restore database backup
cp data/transcriptor.db.backup data/transcriptor.db

# 3. Revert code
git revert <commit-hash>

# 4. Restart
./setup.sh --start
```

---

## ✅ Definition of Done

- [ ] Database migration successful
- [ ] ProcessManager tests pass
- [ ] Integration tests pass
- [ ] RPA tests pass (including new tests 30, 31)
- [ ] Manual test: Upload → Transcribe → Monitor → Stop
- [ ] Manual test: Orphaned cleanup
- [ ] No memory leaks after 10 jobs
- [ ] Documentation updated
- [ ] Code reviewed and approved

---

**Quick Tips:**
- 💾 Always backup database before migration
- 🧪 Test each phase before moving to next
- 📝 Check logs if something fails
- 🔄 Use rollback if needed
- 📞 Ask for help in code review

---

*Generated by system-analyst agent*
*For development-planner handoff*
