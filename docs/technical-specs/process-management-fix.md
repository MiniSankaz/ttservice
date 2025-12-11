# Technical Specification: Process Management Fix

> **Version:** 1.0
> **Date:** 2025-12-11
> **Status:** Draft
> **Author:** system-analyst

---

## 1. ภาพรวม (Overview)

### 1.1 Business Context
ปัจจุบัน TTService มีปัญหาการจัดการ subprocess ที่ใช้สำหรับ transcription ดังนี้:
- เมื่อ user ออกจากหน้า Transcribe ขณะที่กำลังถอดเสียง → subprocess ยังทำงานต่อแต่ไม่มีใครควบคุม
- Process ที่ค้างยังคงใช้ RAM โดยไม่คืนทรัพยากร
- Job status ใน database ยังคงเป็น "processing" แม้ process หลุดไปแล้ว
- User ไม่สามารถดู log ของ job ที่กำลัง processing ได้จากหน้า History

### 1.2 Technical Scope
- สร้าง **ProcessManager** class สำหรับจัดการ lifecycle ของ subprocess
- เพิ่ม **PID tracking** ใน database
- Implement **process cleanup** เมื่อ session หมดอายุหรือ user navigate ออก
- สร้าง **log monitoring** สำหรับ job ที่กำลัง processing

### 1.3 Dependencies
- Streamlit session state management
- SQLite database (transcription_jobs table)
- subprocess module สำหรับ process control
- psutil library สำหรับ advanced process management

---

## 2. สถาปัตยกรรม (Architecture)

### 2.1 Current Architecture

```
User → Streamlit UI → lib/audio.py → subprocess.Popen() → scripts/transcribe_pipeline.py
                                            ↓
                                      [Process ถูกสร้าง แต่ไม่มี tracking]
                                            ↓
                                      User Navigate ออก
                                            ↓
                                      [Process ยังทำงานต่อ, ไม่มีใครควบคุม]
```

**ปัญหา:**
1. ไม่มี PID tracking
2. ไม่มีกลไกทำความสะอาดเมื่อ session หมด
3. ไม่สามารถ attach กลับไปดู log ได้

### 2.2 Proposed Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       Streamlit Web UI                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ Transcribe   │  │   History    │  │   Settings   │          │
│  │   Page       │  │    Page      │  │    Page      │          │
│  └──────┬───────┘  └──────┬───────┘  └──────────────┘          │
└─────────┼──────────────────┼──────────────────────────────────┘
          │                  │
          ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ProcessManager (NEW)                          │
│  ┌────────────────────────────────────────────────────────┐     │
│  │ - register_process(job_id, pid, command)               │     │
│  │ - get_process_status(job_id) → running/stopped         │     │
│  │ - get_process_logs(job_id) → log lines                 │     │
│  │ - kill_process(job_id)                                 │     │
│  │ - cleanup_orphaned_processes()                         │     │
│  └────────────────────────────────────────────────────────┘     │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Database Layer (UPDATED)                      │
│  transcription_jobs:                                             │
│    + process_id (INTEGER, nullable)   ← NEW                     │
│    + log_file_path (TEXT, nullable)   ← NEW                     │
│    + last_heartbeat (TIMESTAMP)       ← NEW                     │
└─────────┬───────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Subprocess Layer                            │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ Process 1    │    │ Process 2    │    │ Log Files    │     │
│  │ PID: 12345   │    │ PID: 12346   │    │ (Tailable)   │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 Data Flow

#### Scenario A: Normal Transcription
```
1. User เริ่ม transcribe → Streamlit สร้าง job_id
2. lib/audio.py สร้าง subprocess → ได้ PID
3. ProcessManager.register_process(job_id, pid, log_path)
4. Database update: job.process_id = pid
5. Subprocess ทำงาน → เขียน log ไปที่ /tmp/transcribe_job_{job_id}.log
6. User ดูหน้า History → ProcessManager.get_process_logs(job_id)
7. Process เสร็จ → ProcessManager cleanup, update status = 'completed'
```

#### Scenario B: User Navigate Out
```
1. User กำลังดูหน้า transcribe (job_id = 123, PID = 45678)
2. User กด Back หรือ navigate ไปหน้าอื่น
3. Streamlit session_state callback trigger
4. ProcessManager.cleanup_orphaned_processes()
   → ตรวจสอบ jobs ที่ status = 'processing'
   → ตรวจสอบว่า PID ยังทำงานอยู่หรือไม่
   → ถ้าไม่มี session ควบคุมแล้ว → kill process
5. Update job status = 'cancelled'
```

#### Scenario C: View Processing Job from History
```
1. User อยู่หน้า History
2. User กด "Monitor" บน job ที่ status = 'processing'
3. show_job_details(job_id) ถูกเรียก
4. ProcessManager.get_process_status(job_id) → "running"
5. ProcessManager.get_process_logs(job_id) → tail -f log file
6. Streamlit แสดง live log ด้วย st.empty() + auto-refresh
```

---

## 3. Database Schema Changes

### 3.1 Migration Script

```sql
-- Migration: 001_add_process_tracking
-- Date: 2025-12-11
-- Description: Add process tracking columns to transcription_jobs

-- Add new columns
ALTER TABLE transcription_jobs ADD COLUMN process_id INTEGER DEFAULT NULL;
ALTER TABLE transcription_jobs ADD COLUMN log_file_path TEXT DEFAULT NULL;
ALTER TABLE transcription_jobs ADD COLUMN last_heartbeat TIMESTAMP DEFAULT NULL;

-- Create index for process_id lookup
CREATE INDEX IF NOT EXISTS idx_jobs_process_id ON transcription_jobs(process_id);

-- Create index for active jobs (processing status + heartbeat)
CREATE INDEX IF NOT EXISTS idx_jobs_active
ON transcription_jobs(status, last_heartbeat)
WHERE status = 'processing';
```

### 3.2 Updated Schema

```python
# app/database.py - Updated table definition

CREATE TABLE transcription_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    original_path TEXT,
    output_path TEXT,
    duration_minutes REAL DEFAULT 0,
    model TEXT DEFAULT 'medium',
    processes INTEGER DEFAULT 2,
    workers INTEGER DEFAULT 8,
    status TEXT DEFAULT 'pending',
    progress REAL DEFAULT 0,
    elapsed_seconds REAL DEFAULT 0,
    speed REAL DEFAULT 0,
    transcript TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,

    -- NEW: Process tracking fields
    process_id INTEGER DEFAULT NULL,              -- PID ของ subprocess หลัก
    log_file_path TEXT DEFAULT NULL,              -- Path ไปยัง log file
    last_heartbeat TIMESTAMP DEFAULT NULL         -- Timestamp ล่าสุดที่ process ยังทำงาน
)
```

### 3.3 New Database Functions

```python
# app/database.py

def register_process(job_id: int, process_id: int, log_file_path: str):
    """Register process ID and log path for a job."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transcription_jobs
            SET process_id = ?,
                log_file_path = ?,
                last_heartbeat = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (process_id, log_file_path, job_id))

def update_heartbeat(job_id: int):
    """Update last heartbeat for a processing job."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transcription_jobs
            SET last_heartbeat = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (job_id,))

def get_active_jobs() -> List[Dict]:
    """Get all jobs that are currently processing."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM transcription_jobs
            WHERE status = 'processing'
            AND process_id IS NOT NULL
        ''')
        return [dict(row) for row in cursor.fetchall()]

def get_orphaned_jobs(timeout_seconds: int = 300) -> List[Dict]:
    """
    Get jobs that are stuck in processing state.
    A job is orphaned if:
    - status = 'processing'
    - last_heartbeat > timeout_seconds ago (no updates)
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM transcription_jobs
            WHERE status = 'processing'
            AND last_heartbeat < datetime('now', '-' || ? || ' seconds')
        ''', (timeout_seconds,))
        return [dict(row) for row in cursor.fetchall()]
```

---

## 4. ProcessManager Class Design

### 4.1 Class Interface

```python
# lib/process_manager.py

from typing import Optional, Dict, List
from pathlib import Path
import subprocess
import psutil
import threading
import time

class ProcessManager:
    """
    จัดการ lifecycle ของ transcription subprocess

    Features:
    - Process registration และ tracking
    - Log file management
    - Process health monitoring
    - Cleanup orphaned processes
    - Live log streaming

    Thread-safe design สำหรับใช้กับ Streamlit
    """

    def __init__(self, log_dir: str = "/tmp"):
        """
        Initialize ProcessManager

        Args:
            log_dir: Directory for storing process logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._monitored_processes: Dict[int, threading.Thread] = {}

    # ========================
    # Process Registration
    # ========================

    def register_process(
        self,
        job_id: int,
        process: subprocess.Popen,
        command: List[str]
    ) -> Dict[str, any]:
        """
        ลงทะเบียน process และสร้าง log file

        Args:
            job_id: Database job ID
            process: subprocess.Popen instance
            command: Command ที่ใช้ run process

        Returns:
            Dict with process info {
                'pid': int,
                'log_path': str,
                'registered': bool
            }
        """

    def unregister_process(self, job_id: int):
        """ยกเลิกการลงทะเบียน process"""

    # ========================
    # Process Status
    # ========================

    def is_process_running(self, job_id: int) -> bool:
        """ตรวจสอบว่า process ยังทำงานอยู่หรือไม่"""

    def get_process_status(self, job_id: int) -> Dict:
        """
        ดึงสถานะของ process

        Returns:
            {
                'running': bool,
                'pid': int or None,
                'cpu_percent': float,
                'memory_mb': float,
                'elapsed_seconds': float
            }
        """

    # ========================
    # Log Management
    # ========================

    def get_log_path(self, job_id: int) -> Optional[Path]:
        """ดึง path ของ log file"""

    def get_logs(
        self,
        job_id: int,
        lines: int = 50,
        follow: bool = False
    ) -> List[str]:
        """
        อ่าน log file

        Args:
            job_id: Job ID
            lines: จำนวนบรรทัดที่ต้องการ (tail -n)
            follow: ถ้า True จะ follow แบบ tail -f

        Returns:
            List of log lines
        """

    def stream_logs(self, job_id: int, callback):
        """
        Stream logs แบบ real-time

        Args:
            job_id: Job ID
            callback: Function(line: str) ที่จะถูกเรียกทุกครั้งที่มีบรรทัดใหม่
        """

    # ========================
    # Process Control
    # ========================

    def kill_process(self, job_id: int, force: bool = False) -> bool:
        """
        หยุด process

        Args:
            job_id: Job ID
            force: ถ้า True ใช้ SIGKILL แทน SIGTERM

        Returns:
            True ถ้าหยุดสำเร็จ
        """

    def kill_process_tree(self, job_id: int) -> bool:
        """หยุด process และ child processes ทั้งหมด"""

    # ========================
    # Cleanup
    # ========================

    def cleanup_orphaned_processes(self, timeout_seconds: int = 300):
        """
        ทำความสะอาด processes ที่ค้าง

        Args:
            timeout_seconds: ถือว่า orphaned ถ้าไม่มี heartbeat เกินนี้
        """

    def cleanup_old_logs(self, days: int = 7):
        """ลบ log files เก่าที่เกิน N วัน"""

    # ========================
    # Monitoring
    # ========================

    def start_monitoring(self, job_id: int, interval_seconds: int = 5):
        """
        เริ่ม background thread เพื่อ monitor process
        และ update heartbeat ใน database
        """

    def stop_monitoring(self, job_id: int):
        """หยุด monitoring thread"""
```

### 4.2 Implementation Details

#### 4.2.1 Process Registration

```python
def register_process(
    self,
    job_id: int,
    process: subprocess.Popen,
    command: List[str]
) -> Dict[str, any]:
    """Implementation"""
    with self._lock:
        pid = process.pid
        log_path = self.log_dir / f"transcribe_job_{job_id}.log"

        # บันทึกใน database
        from app.database import register_process
        register_process(job_id, pid, str(log_path))

        # Start monitoring thread
        self.start_monitoring(job_id)

        return {
            'pid': pid,
            'log_path': str(log_path),
            'registered': True
        }
```

#### 4.2.2 Process Monitoring

```python
def start_monitoring(self, job_id: int, interval_seconds: int = 5):
    """Start background monitoring thread"""
    def monitor_loop():
        from app.database import update_heartbeat, get_job

        while True:
            try:
                job = get_job(job_id)
                if not job or job['status'] != 'processing':
                    break

                # Check if process is still running
                if not self.is_process_running(job_id):
                    # Process died unexpectedly
                    from app.database import fail_job
                    fail_job(job_id, "Process terminated unexpectedly")
                    break

                # Update heartbeat
                update_heartbeat(job_id)

                time.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Monitoring error for job {job_id}: {e}")
                break

        # Cleanup
        self.unregister_process(job_id)

    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
    self._monitored_processes[job_id] = thread
```

#### 4.2.3 Orphaned Process Cleanup

```python
def cleanup_orphaned_processes(self, timeout_seconds: int = 300):
    """Cleanup stuck processes"""
    from app.database import get_orphaned_jobs, fail_job

    orphaned = get_orphaned_jobs(timeout_seconds)

    for job in orphaned:
        job_id = job['id']
        pid = job.get('process_id')

        logger.warning(f"Found orphaned job {job_id} (PID: {pid})")

        # Try to kill process
        if pid and self._is_pid_running(pid):
            self.kill_process_tree(job_id)
            logger.info(f"Killed orphaned process {pid}")

        # Update database
        fail_job(job_id, "Process orphaned and cleaned up")
```

---

## 5. Integration Points

### 5.1 lib/audio.py Changes

```python
# lib/audio.py

def run_transcription(
    input_path: str,
    output_path: str,
    model: str,
    processes: int,
    workers: int,
    progress_callback: Optional[Callable[[str], None]] = None,
    chunk_duration: int = DEFAULT_CHUNK_DURATION,
    overlap_duration: int = DEFAULT_OVERLAP_DURATION,
    job_id: Optional[int] = None  # ← NEW parameter
) -> Dict:
    """
    Run transcription with process tracking
    """
    from lib.process_manager import ProcessManager

    script_path = PROJECT_ROOT / "scripts" / "transcribe_pipeline.py"

    cmd = [
        sys.executable,
        str(script_path),
        input_path,
        output_path,
        '--model', model,
        '--transcribe-processes', str(processes),
        '--transcribe-workers', str(workers),
        '--preprocess-workers', '2',
        '--chunk-duration', str(chunk_duration),
        '--overlap', str(overlap_duration)
    ]

    # Redirect output to log file if job_id provided
    if job_id:
        process_mgr = ProcessManager()
        log_path = process_mgr.log_dir / f"transcribe_job_{job_id}.log"
        log_file = open(log_path, 'w')
        stdout_target = log_file
    else:
        log_file = None
        stdout_target = subprocess.PIPE

    start_time = time.time()

    process = subprocess.Popen(
        cmd,
        stdout=stdout_target,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    # Register process if job_id provided
    if job_id:
        process_mgr.register_process(job_id, process, cmd)

    # Read output
    logs = []
    if log_file:
        # Use log streaming
        for line in process_mgr.stream_logs(job_id, follow=True):
            logs.append(line)
            if progress_callback:
                progress_callback(line)
            if process.poll() is not None:  # Process finished
                break
    else:
        # Original logic
        for line in process.stdout:
            line = line.strip()
            logs.append(line)
            if progress_callback:
                progress_callback(line)

    process.wait()

    if log_file:
        log_file.close()
        process_mgr.stop_monitoring(job_id)

    elapsed = time.time() - start_time
    success = process.returncode == 0

    return {
        'success': success,
        'elapsed_seconds': elapsed,
        'logs': logs
    }
```

### 5.2 web_app.py Changes

#### In show_transcribe_page()

```python
# web_app.py - show_transcribe_page()

# Before running transcription
job_id = create_job(
    filename=uploaded_file.name,
    original_path=str(temp_input),
    duration_minutes=duration,
    model=model,
    processes=processes,
    workers=workers
)

# Pass job_id to run_transcription
result = run_transcription(
    str(temp_input),
    str(output_path),
    model,
    processes,
    workers,
    update_progress,
    chunk_duration,
    overlap_duration,
    job_id=job_id  # ← NEW
)
```

#### In show_job_details() for monitoring

```python
# web_app.py - show_job_details()

def show_job_details(job_id: int):
    """Show detailed view with live log for processing jobs"""
    from lib.process_manager import ProcessManager

    job = get_job(job_id)

    # ... (existing code)

    # For processing jobs, show live logs
    if job['status'] == 'processing':
        st.markdown("### 📊 Live Processing Logs")

        process_mgr = ProcessManager()

        # Check if process is still running
        status = process_mgr.get_process_status(job_id)

        if status['running']:
            # Show process metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("CPU", f"{status['cpu_percent']:.1f}%")
            col2.metric("Memory", f"{status['memory_mb']:.0f} MB")
            col3.metric("Elapsed", f"{status['elapsed_seconds']/60:.1f} min")

            st.markdown("---")

            # Live log area with auto-refresh
            log_placeholder = st.empty()

            # Option to kill process
            if st.button("🛑 Stop Transcription", type="secondary"):
                process_mgr.kill_process_tree(job_id)
                fail_job(job_id, "Stopped by user")
                st.success("Process stopped!")
                time.sleep(1)
                st.rerun()

            # Show last 50 lines of log
            logs = process_mgr.get_logs(job_id, lines=50)
            log_placeholder.code('\n'.join(logs), language='text')

            # Auto-refresh button
            if st.button("🔄 Refresh Logs"):
                st.rerun()

            # Auto-refresh every 5 seconds
            st.markdown("*Auto-refreshing every 5 seconds...*")
            time.sleep(5)
            st.rerun()
        else:
            st.warning("⚠️ Process is no longer running")

            # Show final logs
            logs = process_mgr.get_logs(job_id, lines=100)
            st.code('\n'.join(logs), language='text')

            # Update job status if stuck
            fail_job(job_id, "Process terminated unexpectedly")
```

### 5.3 Session Cleanup Hook

```python
# web_app.py - Add at app initialization

def cleanup_on_session_end():
    """Cleanup processes when user session ends"""
    from lib.process_manager import ProcessManager

    process_mgr = ProcessManager()
    process_mgr.cleanup_orphaned_processes(timeout_seconds=300)

# Register cleanup on page load
if 'cleanup_registered' not in st.session_state:
    import atexit
    atexit.register(cleanup_on_session_end)
    st.session_state.cleanup_registered = True
```

---

## 6. Implementation Plan

### Phase 1: Database Schema (1-2 hours)
**Priority:** P0 (Critical)

**Tasks:**
1. สร้าง migration script: `app/migrations/001_add_process_tracking.sql`
2. เพิ่ม database functions ใน `app/database.py`:
   - `register_process()`
   - `update_heartbeat()`
   - `get_active_jobs()`
   - `get_orphaned_jobs()`
3. เขียน migration runner หรือ run manual:
   ```bash
   sqlite3 data/transcriptor.db < app/migrations/001_add_process_tracking.sql
   ```
4. Test migration กับ existing data

**Verification:**
```bash
# ตรวจสอบ schema
sqlite3 data/transcriptor.db ".schema transcription_jobs"

# Test functions
python -c "from app.database import get_active_jobs; print(get_active_jobs())"
```

---

### Phase 2: ProcessManager Class (3-4 hours)
**Priority:** P0 (Critical)

**Tasks:**
1. สร้างไฟล์ `lib/process_manager.py`
2. Implement core methods:
   - `register_process()`
   - `is_process_running()`
   - `get_process_status()`
   - `kill_process()`
   - `kill_process_tree()`
3. Implement log management:
   - `get_log_path()`
   - `get_logs()`
   - `stream_logs()`
4. Implement monitoring:
   - `start_monitoring()`
   - `stop_monitoring()`
5. Implement cleanup:
   - `cleanup_orphaned_processes()`
   - `cleanup_old_logs()`

**Dependencies:**
```bash
pip install psutil  # For advanced process management
```

**Testing:**
```python
# Test script: tests/test_process_manager.py
from lib.process_manager import ProcessManager
import subprocess
import time

def test_basic_registration():
    pm = ProcessManager()

    # Start dummy process
    proc = subprocess.Popen(['sleep', '10'])

    # Register
    info = pm.register_process(999, proc, ['sleep', '10'])
    assert info['registered']
    assert info['pid'] == proc.pid

    # Check status
    status = pm.get_process_status(999)
    assert status['running']

    # Kill
    pm.kill_process(999)
    time.sleep(1)

    status = pm.get_process_status(999)
    assert not status['running']

if __name__ == '__main__':
    test_basic_registration()
    print("✓ All tests passed")
```

---

### Phase 3: Integration with lib/audio.py (2 hours)
**Priority:** P0 (Critical)

**Tasks:**
1. แก้ไข `run_transcription()` function:
   - เพิ่ม parameter `job_id: Optional[int] = None`
   - สร้าง log file สำหรับ job
   - Register process กับ ProcessManager
   - Start monitoring thread
   - Stream logs แทนการอ่าน stdout โดยตรง
2. Update imports
3. Test การ transcribe ด้วย job_id

**Testing:**
```python
# Manual test
from lib.audio import run_transcription
from app.database import create_job

job_id = create_job(
    filename="test.mp3",
    original_path="/tmp/test.mp3",
    duration_minutes=1.0,
    model="tiny",
    processes=1,
    workers=2
)

result = run_transcription(
    input_path="/tmp/test.mp3",
    output_path="/tmp/test_output.txt",
    model="tiny",
    processes=1,
    workers=2,
    job_id=job_id
)

print(f"Success: {result['success']}")
```

---

### Phase 4: Web UI Integration (3-4 hours)
**Priority:** P1 (High)

**Tasks:**
1. แก้ไข `show_transcribe_page()`:
   - ส่ง `job_id` ไปยัง `run_transcription()`
2. แก้ไข `show_job_details()`:
   - เพิ่ม live log viewer สำหรับ processing jobs
   - แสดง process metrics (CPU, Memory)
   - เพิ่มปุ่ม "Stop Transcription"
   - Implement auto-refresh ทุก 5 วินาที
3. เพิ่ม session cleanup hook:
   - Call `cleanup_orphaned_processes()` on app init
4. Test UI flow ทั้งหมด

**UI Components:**
```python
# Live Log Viewer Component
def render_live_logs(job_id: int):
    """Render live log viewer with auto-refresh"""
    from lib.process_manager import ProcessManager

    pm = ProcessManager()
    status = pm.get_process_status(job_id)

    if status['running']:
        # Metrics
        col1, col2, col3 = st.columns(3)
        col1.metric("CPU", f"{status['cpu_percent']:.1f}%")
        col2.metric("Memory", f"{status['memory_mb']:.0f} MB")
        col3.metric("Elapsed", f"{status['elapsed_seconds']/60:.1f} min")

        # Logs
        logs = pm.get_logs(job_id, lines=50)
        st.code('\n'.join(logs), language='text')

        # Control buttons
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("🛑 Stop"):
                pm.kill_process_tree(job_id)
                st.rerun()
        with col2:
            if st.button("🔄 Refresh"):
                st.rerun()

        # Auto-refresh
        time.sleep(5)
        st.rerun()
    else:
        st.warning("Process is no longer running")
        logs = pm.get_logs(job_id, lines=100)
        st.code('\n'.join(logs), language='text')
```

---

### Phase 5: Testing & Validation (2-3 hours)
**Priority:** P0 (Critical)

**Test Scenarios:**

#### Test 1: Normal Transcription Flow
```
✓ User uploads file
✓ Start transcription → PID registered
✓ Monitor logs in real-time
✓ Process completes → Status updated
✓ Log file exists
```

#### Test 2: User Navigate Away
```
✓ User starts transcription
✓ User navigates to History page
✓ Process continues in background
✓ User can monitor from History
✓ Process completes normally
```

#### Test 3: Kill Running Process
```
✓ User starts transcription
✓ Go to History → Monitor
✓ Click "Stop Transcription"
✓ Process killed
✓ Status = 'cancelled'
✓ Resources freed
```

#### Test 4: Orphaned Process Cleanup
```
✓ Simulate stuck process (manual PID injection)
✓ Set old heartbeat timestamp
✓ Call cleanup_orphaned_processes()
✓ Process killed
✓ Status updated
```

#### Test 5: Multiple Concurrent Jobs
```
✓ Start 3 transcriptions simultaneously
✓ Each gets unique PID
✓ Monitor all from History
✓ Kill one → others continue
✓ All complete successfully
```

**RPA Test Updates:**
```python
# tests/rpa_web_test.py

def test_30_process_tracking():
    """Test process tracking and monitoring"""
    # Upload file
    # Start transcription
    # Get job_id from database
    # Verify PID registered
    # Navigate away
    # Go to History → Monitor
    # Verify logs visible
    # Stop process
    # Verify status updated

def test_31_orphan_cleanup():
    """Test orphaned process cleanup"""
    # Create fake orphaned job in DB
    # Call cleanup API
    # Verify job status updated
```

---

### Phase 6: Documentation & Deployment (1 hour)
**Priority:** P2 (Medium)

**Tasks:**
1. Update `.claude/KNOWN_ISSUES.md`:
   - ลบ issue เก่าที่แก้แล้ว
   - เพิ่ม issue ใหม่ (ถ้ามี)
2. Update `CLAUDE.md`:
   - เพิ่ม ProcessManager ใน architecture section
3. สร้าง migration guide:
   ```markdown
   # Migration Guide: Process Management

   ## Database Migration
   ```bash
   sqlite3 data/transcriptor.db < app/migrations/001_add_process_tracking.sql
   ```

   ## Install Dependencies
   ```bash
   pip install psutil
   ```

   ## Restart Application
   ```bash
   ./setup.sh --stop
   ./setup.sh --start
   ```
   ```
4. Update CHANGELOG

---

## 7. Risk Assessment & Mitigation

### Risk 1: Process Leak
**Risk:** ProcessManager fails to kill process → memory leak

**Impact:** HIGH
**Probability:** MEDIUM

**Mitigation:**
- Implement multi-level kill: SIGTERM → wait 5s → SIGKILL
- Use `psutil` to kill entire process tree (includes child processes)
- Add health check job: cleanup every 10 minutes
- Implement resource limits using `ulimit` or `cgroups`

**Code:**
```python
def kill_process_tree(self, job_id: int, timeout: int = 5) -> bool:
    """Kill process with fallback"""
    try:
        proc = psutil.Process(pid)

        # Try graceful shutdown
        proc.terminate()
        proc.wait(timeout)

        if proc.is_running():
            # Force kill
            proc.kill()
            proc.wait(timeout)

        # Kill children
        for child in proc.children(recursive=True):
            try:
                child.kill()
            except:
                pass

        return True
    except Exception as e:
        logger.error(f"Failed to kill process tree: {e}")
        return False
```

---

### Risk 2: Log File Growth
**Risk:** Log files grow too large → disk full

**Impact:** MEDIUM
**Probability:** MEDIUM

**Mitigation:**
- Implement log rotation: max 10MB per file
- Auto-delete logs older than 7 days
- Compress old logs using gzip
- Add disk space check before starting transcription

**Code:**
```python
def cleanup_old_logs(self, days: int = 7):
    """Delete old log files"""
    cutoff = datetime.now() - timedelta(days=days)

    for log_file in self.log_dir.glob("transcribe_job_*.log"):
        if log_file.stat().st_mtime < cutoff.timestamp():
            # Compress before delete
            if log_file.stat().st_size > 1024 * 1024:  # > 1MB
                with gzip.open(f"{log_file}.gz", 'wb') as gz:
                    gz.write(log_file.read_bytes())

            log_file.unlink()
            logger.info(f"Deleted old log: {log_file}")
```

---

### Risk 3: Race Condition
**Risk:** Multiple threads accessing same process → race condition

**Impact:** MEDIUM
**Probability:** LOW

**Mitigation:**
- Use `threading.Lock()` for all ProcessManager operations
- Thread-safe database operations with transaction
- Atomic PID checks using psutil
- Test with concurrent job execution

**Code:**
```python
class ProcessManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._db_lock = threading.Lock()

    def register_process(self, job_id, process, command):
        with self._lock:
            # Thread-safe registration
            ...
```

---

### Risk 4: Database Corruption
**Risk:** Power failure during database write → corrupted database

**Impact:** HIGH
**Probability:** LOW

**Mitigation:**
- Enable SQLite WAL mode for better concurrency
- Add database backup before migration
- Implement database health check on startup
- Add transaction rollback on error

**Code:**
```python
# app/database.py

def init_database():
    """Initialize database with WAL mode"""
    with get_connection() as conn:
        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')

        # Create tables...
```

---

### Risk 5: Performance Impact
**Risk:** Monitoring threads consume too much CPU

**Impact:** LOW
**Probability:** LOW

**Mitigation:**
- Use 5-second interval for heartbeat updates
- Use efficient process checks with psutil
- Limit concurrent monitoring threads
- Profile and optimize hot paths

**Code:**
```python
def start_monitoring(self, job_id: int, interval_seconds: int = 5):
    """Lightweight monitoring"""
    def monitor_loop():
        while True:
            try:
                # Quick PID check (no full process info)
                if not psutil.pid_exists(pid):
                    break

                # Update heartbeat (cheap DB write)
                update_heartbeat(job_id)

                time.sleep(interval_seconds)
            except:
                break

    # Daemon thread (won't block app exit)
    thread = threading.Thread(target=monitor_loop, daemon=True)
    thread.start()
```

---

## 8. Performance Considerations

### 8.1 Memory Usage
**Before:**
- Orphaned processes: ~1-2 GB per process
- No cleanup → memory grows indefinitely

**After:**
- ProcessManager overhead: ~5 MB
- Monitoring threads: ~1 MB per job
- Log files: ~10 MB per job (with rotation)

**Expected Impact:**
- Minimal overhead (~1% CPU, ~10 MB RAM)
- Prevents memory leaks (saves GBs)

### 8.2 Database Performance
**Queries Added:**
- `SELECT` for active jobs: < 1ms (indexed)
- `UPDATE` heartbeat: < 1ms (single row)
- `SELECT` orphaned jobs: < 5ms (indexed + date filter)

**Index Strategy:**
```sql
CREATE INDEX idx_jobs_process_id ON transcription_jobs(process_id);
CREATE INDEX idx_jobs_active ON transcription_jobs(status, last_heartbeat)
WHERE status = 'processing';
```

### 8.3 UI Responsiveness
**Live Log Viewer:**
- Refresh interval: 5 seconds
- Log tail: 50 lines (fast read)
- Process metrics: cached in memory

**Optimization:**
- Use `st.empty()` for updates (no re-render)
- Lazy load full logs (only on demand)
- Cancel monitoring when user navigates away

---

## 9. Security Considerations

### 9.1 Process Access Control
**Concern:** User could kill other users' processes

**Mitigation:**
- No multi-user support yet (single-user app)
- Future: Add user_id to jobs table
- Validate job ownership before kill

### 9.2 Log File Access
**Concern:** Sensitive data in logs

**Mitigation:**
- Store logs in `/tmp` (auto-cleanup on reboot)
- Set restrictive permissions: `chmod 600`
- Don't log audio file contents
- Sanitize filenames in logs

### 9.3 Command Injection
**Concern:** Malicious filenames → command injection

**Mitigation:**
- Already using `subprocess.Popen(list)` (safe)
- Validate filenames before processing
- Use `shlex.quote()` for shell commands

---

## 10. Monitoring & Observability

### 10.1 Metrics to Track
```python
# ProcessManager metrics
metrics = {
    'active_processes': len(get_active_jobs()),
    'orphaned_cleaned': cleanup_count,
    'total_cpu_usage': sum(p.cpu_percent() for p in active),
    'total_memory_mb': sum(p.memory_info().rss / 1024 / 1024 for p in active),
    'log_files_count': len(list(log_dir.glob('*.log'))),
    'log_files_size_mb': sum(f.stat().st_size for f in log_dir.glob('*.log')) / 1024 / 1024
}
```

### 10.2 Health Check Endpoint
```python
# Add to Settings page or CLI

def health_check():
    """Check ProcessManager health"""
    pm = ProcessManager()

    # Check for orphaned jobs
    orphaned = get_orphaned_jobs(timeout_seconds=300)

    # Check for stuck processes
    stuck = []
    for job in get_active_jobs():
        if not pm.is_process_running(job['id']):
            stuck.append(job)

    return {
        'status': 'healthy' if not stuck else 'degraded',
        'orphaned_count': len(orphaned),
        'stuck_count': len(stuck),
        'active_count': len(get_active_jobs()),
    }
```

### 10.3 Logging Strategy
```python
# ProcessManager logging
logger = logging.getLogger('process_manager')

# Log levels:
# INFO: Process lifecycle events (start, stop, cleanup)
# WARNING: Orphaned process detected
# ERROR: Failed to kill process
# DEBUG: Detailed process metrics
```

---

## 11. Testing Strategy

### 11.1 Unit Tests
```python
# tests/unit/test_process_manager.py

import unittest
from lib.process_manager import ProcessManager
import subprocess
import time

class TestProcessManager(unittest.TestCase):
    def setUp(self):
        self.pm = ProcessManager(log_dir="/tmp/test_pm")

    def test_register_process(self):
        """Test process registration"""
        proc = subprocess.Popen(['sleep', '5'])
        info = self.pm.register_process(1, proc, ['sleep', '5'])

        self.assertTrue(info['registered'])
        self.assertEqual(info['pid'], proc.pid)
        self.assertIsNotNone(info['log_path'])

    def test_is_process_running(self):
        """Test process status check"""
        proc = subprocess.Popen(['sleep', '5'])
        self.pm.register_process(1, proc, ['sleep', '5'])

        self.assertTrue(self.pm.is_process_running(1))

        proc.kill()
        time.sleep(0.5)

        self.assertFalse(self.pm.is_process_running(1))

    def test_kill_process(self):
        """Test process termination"""
        proc = subprocess.Popen(['sleep', '10'])
        self.pm.register_process(1, proc, ['sleep', '10'])

        self.assertTrue(self.pm.kill_process(1))
        time.sleep(1)

        self.assertFalse(self.pm.is_process_running(1))

    def test_get_logs(self):
        """Test log reading"""
        # Create log file
        log_path = self.pm.log_dir / "transcribe_job_1.log"
        log_path.write_text("line1\nline2\nline3\n")

        logs = self.pm.get_logs(1, lines=2)

        self.assertEqual(len(logs), 2)
        self.assertEqual(logs[-1], "line3")
```

### 11.2 Integration Tests
```python
# tests/integration/test_transcription_with_tracking.py

def test_full_transcription_flow():
    """Test complete transcription with process tracking"""
    from lib.audio import run_transcription
    from app.database import create_job, get_job
    from lib.process_manager import ProcessManager

    # Create job
    job_id = create_job(
        filename="test.mp3",
        original_path="/tmp/test.mp3",
        duration_minutes=1.0,
        model="tiny",
        processes=1,
        workers=2
    )

    # Run transcription
    result = run_transcription(
        input_path="/tmp/test.mp3",
        output_path="/tmp/test_output.txt",
        model="tiny",
        processes=1,
        workers=2,
        job_id=job_id
    )

    # Verify
    assert result['success']

    job = get_job(job_id)
    assert job['status'] == 'completed'
    assert job['process_id'] is not None
    assert job['log_file_path'] is not None

    # Verify log file exists
    pm = ProcessManager()
    log_path = pm.get_log_path(job_id)
    assert log_path.exists()

    # Verify logs readable
    logs = pm.get_logs(job_id)
    assert len(logs) > 0
```

### 11.3 RPA Tests (Selenium)
```python
# tests/rpa_web_test.py

def test_30_monitor_processing_job(driver):
    """Test monitoring a processing job from History"""
    # Upload file
    driver.get("http://localhost:8501")
    # ... upload and start transcription ...

    # Navigate to History
    driver.find_element(By.LINK_TEXT, "History").click()
    time.sleep(2)

    # Find processing job
    monitor_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Monitor')]")
    monitor_btn.click()
    time.sleep(2)

    # Verify live logs visible
    logs_element = driver.find_element(By.TAG_NAME, "code")
    assert len(logs_element.text) > 0

    # Verify metrics visible
    assert "CPU" in driver.page_source
    assert "Memory" in driver.page_source

    # Test stop button
    stop_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Stop')]")
    stop_btn.click()
    time.sleep(2)

    # Verify job cancelled
    assert "cancelled" in driver.page_source.lower()

def test_31_cleanup_orphaned_jobs(driver):
    """Test orphaned job cleanup"""
    # Create fake orphaned job (manual DB injection)
    from app.database import create_job, register_process
    from datetime import datetime, timedelta

    job_id = create_job(
        filename="orphaned.mp3",
        original_path="/tmp/orphaned.mp3",
        duration_minutes=1.0,
        model="tiny",
        processes=1,
        workers=2
    )

    # Register fake PID and old heartbeat
    register_process(job_id, 99999, "/tmp/fake.log")

    # Manually set old heartbeat
    from app.database import get_connection
    with get_connection() as conn:
        old_time = datetime.now() - timedelta(minutes=10)
        conn.execute(
            "UPDATE transcription_jobs SET last_heartbeat = ? WHERE id = ?",
            (old_time, job_id)
        )

    # Trigger cleanup
    from lib.process_manager import ProcessManager
    pm = ProcessManager()
    pm.cleanup_orphaned_processes(timeout_seconds=300)

    # Verify job marked as failed
    from app.database import get_job
    job = get_job(job_id)
    assert job['status'] == 'failed'
    assert 'orphaned' in job['error_message'].lower()
```

---

## 12. Rollback Plan

### If Critical Issues Found:

#### Rollback Step 1: Disable ProcessManager
```python
# lib/audio.py

def run_transcription(..., job_id=None):
    # Temporarily disable process tracking
    USE_PROCESS_TRACKING = False

    if USE_PROCESS_TRACKING and job_id:
        # New code
        ...
    else:
        # Fallback to original code
        ...
```

#### Rollback Step 2: Database Rollback
```sql
-- Rollback migration
ALTER TABLE transcription_jobs DROP COLUMN process_id;
ALTER TABLE transcription_jobs DROP COLUMN log_file_path;
ALTER TABLE transcription_jobs DROP COLUMN last_heartbeat;

DROP INDEX IF EXISTS idx_jobs_process_id;
DROP INDEX IF EXISTS idx_jobs_active;
```

#### Rollback Step 3: Remove Dependencies
```bash
pip uninstall psutil
```

#### Rollback Step 4: Git Revert
```bash
git revert <commit-hash>
git push
```

---

## 13. Success Criteria

### Must Have (P0):
- ✅ PID tracking ใน database
- ✅ Process cleanup เมื่อ session หมด
- ✅ Kill orphaned processes
- ✅ View logs ของ processing jobs จาก History

### Should Have (P1):
- ✅ Live log viewer with auto-refresh
- ✅ Process metrics (CPU, Memory)
- ✅ Stop button for running jobs
- ✅ Cleanup old log files

### Nice to Have (P2):
- ⬜ Process resource limits
- ⬜ Email notification เมื่อ job เสร็จ
- ⬜ Prometheus metrics endpoint
- ⬜ Distributed process management (multi-server)

---

## 14. Appendix

### A. Dependencies
```bash
# requirements.txt additions
psutil>=5.9.0  # Process management
```

### B. File Structure After Implementation
```
ttservice/
├── lib/
│   ├── audio.py (MODIFIED)
│   └── process_manager.py (NEW)
│
├── app/
│   ├── database.py (MODIFIED)
│   └── migrations/
│       └── 001_add_process_tracking.sql (NEW)
│
├── web_app.py (MODIFIED)
│
├── tests/
│   ├── unit/
│   │   └── test_process_manager.py (NEW)
│   ├── integration/
│   │   └── test_transcription_with_tracking.py (NEW)
│   └── rpa_web_test.py (MODIFIED)
│
└── docs/
    └── technical-specs/
        └── process-management-fix.md (THIS FILE)
```

### C. Related Documents
- `.claude/PROJECT_CONTEXT.md` - Project architecture
- `.claude/KNOWN_ISSUES.md` - Known issues tracker
- `CLAUDE.md` - Development guide
- `docs/technical-specs/llm-refinement-analysis.md` - Previous tech spec example

### D. Glossary
- **PID**: Process ID (Unix process identifier)
- **Orphaned Process**: Process ที่ไม่มี parent process ควบคุม
- **Heartbeat**: Periodic signal ที่บอกว่า process ยังทำงานอยู่
- **Process Tree**: Process และ child processes ทั้งหมด
- **SIGTERM**: Graceful shutdown signal (can be caught)
- **SIGKILL**: Force kill signal (cannot be caught)

---

**Document Status:** Draft
**Next Review:** After Phase 1 completion
**Approval Required:** development-planner

---

*Generated by system-analyst agent*
*TTService v1.0.0*
