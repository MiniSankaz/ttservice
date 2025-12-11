"""
Process Manager - Centralized subprocess management for Transcriptor

Handles:
- Process lifecycle (start, stop, kill)
- Heartbeat monitoring
- Log management
- Orphan process cleanup
- Resource tracking (PID, memory)

Usage:
    from lib.process_manager import ProcessManager

    pm = ProcessManager()

    # Start a transcription process
    process = pm.start_process(job_id, cmd)

    # Check if running
    if pm.is_running(job_id):
        logs = pm.get_logs(job_id)

    # Stop process
    pm.stop_process(job_id)

    # Cleanup orphans
    pm.cleanup_orphans()
"""

import os
import re
import signal
import subprocess
import threading
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class ProcessInfo:
    """Information about a running process."""
    job_id: int
    process: subprocess.Popen
    pid: int
    cmd: List[str]
    log_file: Path
    start_time: datetime = field(default_factory=datetime.now)
    logs: List[str] = field(default_factory=list)
    progress: float = 0.0
    status: str = "running"


class ProcessManager:
    """
    Centralized manager for transcription subprocesses.

    Features:
    - Track all running processes by job_id
    - Heartbeat thread for health monitoring
    - Log capture and retrieval
    - Graceful shutdown with SIGTERM/SIGKILL fallback
    - Orphan detection and cleanup
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern for process manager."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._processes: Dict[int, ProcessInfo] = {}
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_running = False
        self._heartbeat_interval = 5  # seconds
        self._log_dir = PROJECT_ROOT / "logs" / "jobs"
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._initialized = True

        # Start heartbeat thread
        self._start_heartbeat_thread()

        logger.info("ProcessManager initialized")

    def start_process(
        self,
        job_id: int,
        cmd: List[str],
        progress_callback: Optional[Callable[[str], None]] = None,
        env: Optional[Dict] = None
    ) -> subprocess.Popen:
        """
        Start a new subprocess and track it.

        Args:
            job_id: Unique job identifier
            cmd: Command to execute
            progress_callback: Optional callback for log lines
            env: Optional environment variables

        Returns:
            The subprocess.Popen object
        """
        # Create log file
        log_file = self._log_dir / f"job_{job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

        # Start process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env or os.environ.copy()
        )

        # Create process info
        proc_info = ProcessInfo(
            job_id=job_id,
            process=process,
            pid=process.pid,
            cmd=cmd,
            log_file=log_file
        )

        self._processes[job_id] = proc_info

        # Start log reader thread
        log_thread = threading.Thread(
            target=self._read_process_output,
            args=(job_id, progress_callback),
            daemon=True
        )
        log_thread.start()

        logger.info(f"[Job {job_id}] Started process PID={process.pid}")

        # Update database
        try:
            from app.database import update_job_status
            update_job_status(
                job_id=job_id,
                status='processing',
                pid=process.pid,
                log_file=str(log_file)
            )
        except Exception as e:
            logger.warning(f"Failed to update database: {e}")

        return process

    def _read_process_output(
        self,
        job_id: int,
        progress_callback: Optional[Callable[[str], None]] = None
    ):
        """Read process output and store in logs."""
        proc_info = self._processes.get(job_id)
        if not proc_info:
            return

        try:
            with open(proc_info.log_file, 'w', encoding='utf-8') as log_f:
                for line in proc_info.process.stdout:
                    line = line.rstrip('\n')

                    # Store in memory (keep last 1000 lines)
                    proc_info.logs.append(line)
                    if len(proc_info.logs) > 1000:
                        proc_info.logs.pop(0)

                    # Write to log file
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    log_f.write(f"[{timestamp}] {line}\n")
                    log_f.flush()

                    # Call progress callback
                    if progress_callback:
                        try:
                            progress_callback(line)
                        except Exception as e:
                            logger.warning(f"Progress callback error: {e}")

                    # Parse progress and update database
                    self._parse_progress(proc_info, line, job_id)

            # Process completed
            proc_info.process.wait()
            proc_info.status = "completed" if proc_info.process.returncode == 0 else "failed"

        except Exception as e:
            logger.error(f"[Job {job_id}] Error reading output: {e}")
            proc_info.status = "error"

    def _parse_progress(self, proc_info: ProcessInfo, line: str, job_id: int):
        """Parse progress from log line and update database."""

        # Look for percentage patterns
        match = re.search(r'(\d+\.?\d*)%', line)
        if match:
            try:
                new_progress = float(match.group(1))
                # Only update if progress changed significantly (reduce DB writes)
                if abs(new_progress - proc_info.progress) >= 1.0:
                    proc_info.progress = new_progress
                    # Update database
                    try:
                        from app.database import update_job_status
                        update_job_status(job_id, 'processing', progress=new_progress)
                    except Exception as e:
                        logger.warning(f"Failed to update progress: {e}")
            except ValueError:
                pass

    def stop_process(self, job_id: int, timeout: float = 10.0) -> bool:
        """
        Stop a process gracefully, then force kill if needed.

        Args:
            job_id: Job identifier
            timeout: Seconds to wait before force kill

        Returns:
            True if process was stopped
        """
        proc_info = self._processes.get(job_id)
        if not proc_info:
            logger.warning(f"[Job {job_id}] No process found")
            return False

        process = proc_info.process

        if process.poll() is not None:
            # Already terminated
            logger.info(f"[Job {job_id}] Process already terminated")
            self._cleanup_process(job_id)
            return True

        try:
            # Try graceful termination
            logger.info(f"[Job {job_id}] Sending SIGTERM to PID={process.pid}")
            process.terminate()

            # Wait for graceful shutdown
            try:
                process.wait(timeout=timeout)
                logger.info(f"[Job {job_id}] Process terminated gracefully")
            except subprocess.TimeoutExpired:
                # Force kill
                logger.warning(f"[Job {job_id}] SIGTERM timeout, sending SIGKILL")
                process.kill()
                process.wait(timeout=5)
                logger.info(f"[Job {job_id}] Process killed")

            proc_info.status = "cancelled"
            self._cleanup_process(job_id)

            # Update database
            try:
                from app.database import cancel_job
                cancel_job(job_id, "Cancelled by user")
            except Exception as e:
                logger.warning(f"Failed to update database: {e}")

            return True

        except Exception as e:
            logger.error(f"[Job {job_id}] Failed to stop process: {e}")
            return False

    def kill_process(self, job_id: int) -> bool:
        """Force kill a process immediately."""
        proc_info = self._processes.get(job_id)
        if not proc_info:
            return False

        try:
            proc_info.process.kill()
            proc_info.process.wait(timeout=5)
            proc_info.status = "killed"
            self._cleanup_process(job_id)
            return True
        except Exception as e:
            logger.error(f"[Job {job_id}] Failed to kill: {e}")
            return False

    def _cleanup_process(self, job_id: int):
        """Remove process from tracking."""
        if job_id in self._processes:
            del self._processes[job_id]
            logger.info(f"[Job {job_id}] Removed from process manager")

    def is_running(self, job_id: int) -> bool:
        """Check if a process is running."""
        proc_info = self._processes.get(job_id)
        if not proc_info:
            return False
        return proc_info.process.poll() is None

    def get_process_info(self, job_id: int) -> Optional[ProcessInfo]:
        """Get process info."""
        return self._processes.get(job_id)

    def get_logs(self, job_id: int, last_n: int = 100) -> List[str]:
        """Get recent log lines for a job."""
        proc_info = self._processes.get(job_id)
        if proc_info:
            return proc_info.logs[-last_n:]

        # Try to read from log file
        try:
            from app.database import get_job_log_file
            log_file = get_job_log_file(job_id)
            if log_file and Path(log_file).exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    return [line.rstrip('\n') for line in lines[-last_n:]]
        except Exception as e:
            logger.warning(f"Failed to read log file: {e}")

        return []

    def get_progress(self, job_id: int) -> float:
        """Get current progress percentage."""
        proc_info = self._processes.get(job_id)
        return proc_info.progress if proc_info else 0.0

    def get_all_running(self) -> Dict[int, ProcessInfo]:
        """Get all running processes."""
        return {
            job_id: info
            for job_id, info in self._processes.items()
            if info.process.poll() is None
        }

    # ==================== Heartbeat ====================

    def _start_heartbeat_thread(self):
        """Start the heartbeat monitoring thread."""
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            return

        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True
        )
        self._heartbeat_thread.start()
        logger.info("Heartbeat thread started")

    def _heartbeat_loop(self):
        """Heartbeat loop - update database periodically."""
        while self._heartbeat_running:
            try:
                self._update_heartbeats()
                self._check_orphans()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")

            time.sleep(self._heartbeat_interval)

    def _update_heartbeats(self):
        """Update heartbeat for all running processes."""
        try:
            from app.database import update_heartbeat

            for job_id, proc_info in list(self._processes.items()):
                if proc_info.process.poll() is None:
                    update_heartbeat(job_id)
                else:
                    # Process ended, cleanup
                    self._cleanup_process(job_id)

        except Exception as e:
            logger.warning(f"Failed to update heartbeats: {e}")

    def _check_orphans(self):
        """Check for orphaned processes in database."""
        try:
            from app.database import get_orphaned_jobs, cleanup_stale_jobs

            # Get orphaned jobs from database
            orphaned = get_orphaned_jobs(timeout_seconds=60)

            for job in orphaned:
                job_id = job['id']
                pid = job.get('pid')

                if pid and job_id not in self._processes:
                    # Try to kill orphaned process
                    try:
                        os.kill(pid, signal.SIGTERM)
                        logger.info(f"Killed orphaned process PID={pid} (Job {job_id})")
                    except ProcessLookupError:
                        pass  # Process already dead
                    except PermissionError:
                        logger.warning(f"Cannot kill PID={pid}, permission denied")

            # Cleanup stale jobs in database
            cleaned = cleanup_stale_jobs()
            if cleaned > 0:
                logger.info(f"Cleaned up {cleaned} stale jobs")

        except Exception as e:
            logger.warning(f"Orphan check error: {e}")

    def cleanup_orphans(self) -> int:
        """Manual orphan cleanup."""
        try:
            from app.database import cleanup_stale_jobs
            return cleanup_stale_jobs()
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
            return 0

    def stop_heartbeat(self):
        """Stop the heartbeat thread."""
        self._heartbeat_running = False
        if self._heartbeat_thread:
            self._heartbeat_thread.join(timeout=2)

    def shutdown(self):
        """Shutdown all processes and cleanup."""
        logger.info("Shutting down ProcessManager...")

        # Stop all running processes
        for job_id in list(self._processes.keys()):
            self.stop_process(job_id, timeout=5)

        # Stop heartbeat
        self.stop_heartbeat()

        logger.info("ProcessManager shutdown complete")


# Global instance
_process_manager: Optional[ProcessManager] = None


def get_process_manager() -> ProcessManager:
    """Get the global ProcessManager instance."""
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager()
    return _process_manager
