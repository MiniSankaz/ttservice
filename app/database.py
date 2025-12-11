"""
SQLite Database Module for Transcriptor Pipeline

Handles all database operations for transcription history and job management.
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
import json

# Database path
DB_PATH = Path(__file__).parent.parent / "data" / "transcriptor.db"


def get_db_path() -> Path:
    """Get database path, ensuring directory exists."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH


@contextmanager
def get_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize database with required tables."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Transcription jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transcription_jobs (
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
                pid INTEGER,
                heartbeat TIMESTAMP,
                log_file TEXT
            )
        ''')

        # Migration: Add new columns if they don't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE transcription_jobs ADD COLUMN pid INTEGER')
        except sqlite3.OperationalError:
            pass  # Column already exists
        try:
            cursor.execute('ALTER TABLE transcription_jobs ADD COLUMN heartbeat TIMESTAMP')
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute('ALTER TABLE transcription_jobs ADD COLUMN log_file TEXT')
        except sqlite3.OperationalError:
            pass

        # Settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Statistics table (for caching)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY,
                total_jobs INTEGER DEFAULT 0,
                successful_jobs INTEGER DEFAULT 0,
                failed_jobs INTEGER DEFAULT 0,
                total_audio_minutes REAL DEFAULT 0,
                total_processing_minutes REAL DEFAULT 0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_status ON transcription_jobs(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_created ON transcription_jobs(created_at DESC)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_pid ON transcription_jobs(pid)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_jobs_heartbeat ON transcription_jobs(heartbeat)')

        conn.commit()


# ==================== Job Operations ====================

def create_job(
    filename: str,
    original_path: str,
    duration_minutes: float = 0,
    model: str = 'medium',
    processes: int = 2,
    workers: int = 8
) -> int:
    """Create a new transcription job."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO transcription_jobs
            (filename, original_path, duration_minutes, model, processes, workers, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (filename, original_path, duration_minutes, model, processes, workers))
        return cursor.lastrowid


def update_job_status(
    job_id: int,
    status: str,
    progress: float = None,
    error_message: str = None,
    pid: int = None,
    log_file: str = None
):
    """Update job status."""
    with get_connection() as conn:
        cursor = conn.cursor()

        updates = ['status = ?']
        params = [status]

        if progress is not None:
            updates.append('progress = ?')
            params.append(progress)

        if error_message is not None:
            updates.append('error_message = ?')
            params.append(error_message)

        if pid is not None:
            updates.append('pid = ?')
            params.append(pid)

        if log_file is not None:
            updates.append('log_file = ?')
            params.append(log_file)

        if status == 'processing':
            updates.append('started_at = CURRENT_TIMESTAMP')
            updates.append('heartbeat = CURRENT_TIMESTAMP')
        elif status in ['completed', 'failed', 'cancelled']:
            updates.append('completed_at = CURRENT_TIMESTAMP')
            updates.append('pid = NULL')

        params.append(job_id)

        cursor.execute(f'''
            UPDATE transcription_jobs
            SET {', '.join(updates)}
            WHERE id = ?
        ''', params)


def complete_job(
    job_id: int,
    output_path: str,
    transcript: str,
    elapsed_seconds: float,
    speed: float
):
    """Mark job as completed with results."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transcription_jobs
            SET status = 'completed',
                output_path = ?,
                transcript = ?,
                elapsed_seconds = ?,
                speed = ?,
                progress = 100,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (output_path, transcript, elapsed_seconds, speed, job_id))


def fail_job(job_id: int, error_message: str):
    """Mark job as failed with error message."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transcription_jobs
            SET status = 'failed',
                error_message = ?,
                completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (error_message, job_id))


def get_job(job_id: int) -> Optional[Dict]:
    """Get job by ID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM transcription_jobs WHERE id = ?', (job_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_jobs(
    status: str = None,
    limit: int = 100,
    offset: int = 0
) -> List[Dict]:
    """Get jobs with optional filtering."""
    with get_connection() as conn:
        cursor = conn.cursor()

        query = 'SELECT * FROM transcription_jobs'
        params = []

        if status:
            query += ' WHERE status = ?'
            params.append(status)

        query += ' ORDER BY created_at DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])

        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_recent_jobs(limit: int = 10) -> List[Dict]:
    """Get recent jobs."""
    return get_jobs(limit=limit)


def delete_job(job_id: int):
    """Delete a job."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transcription_jobs WHERE id = ?', (job_id,))


def clear_all_jobs():
    """Delete all jobs."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM transcription_jobs')


# ==================== Process Management ====================

def update_heartbeat(job_id: int):
    """Update job heartbeat timestamp."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transcription_jobs
            SET heartbeat = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (job_id,))


def get_active_jobs() -> List[Dict]:
    """Get all active (processing) jobs with PID."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM transcription_jobs
            WHERE status = 'processing' AND pid IS NOT NULL
            ORDER BY started_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_orphaned_jobs(timeout_seconds: int = 60) -> List[Dict]:
    """Get jobs that appear to be orphaned (no heartbeat update)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM transcription_jobs
            WHERE status = 'processing'
            AND (
                heartbeat IS NULL
                OR datetime(heartbeat) < datetime('now', ? || ' seconds')
            )
        ''', (f'-{timeout_seconds}',))
        return [dict(row) for row in cursor.fetchall()]


def cancel_job(job_id: int, reason: str = 'Cancelled by user'):
    """Mark job as cancelled."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE transcription_jobs
            SET status = 'cancelled',
                error_message = ?,
                completed_at = CURRENT_TIMESTAMP,
                pid = NULL
            WHERE id = ?
        ''', (reason, job_id))


def get_job_log_file(job_id: int) -> Optional[str]:
    """Get log file path for a job."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT log_file FROM transcription_jobs WHERE id = ?', (job_id,))
        row = cursor.fetchone()
        return row['log_file'] if row else None


def cleanup_stale_jobs():
    """Mark stale processing jobs as failed."""
    orphaned = get_orphaned_jobs(timeout_seconds=120)  # 2 minutes timeout
    for job in orphaned:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE transcription_jobs
                SET status = 'failed',
                    error_message = 'Process terminated unexpectedly (no heartbeat)',
                    completed_at = CURRENT_TIMESTAMP,
                    pid = NULL
                WHERE id = ?
            ''', (job['id'],))
    return len(orphaned)


# ==================== Statistics ====================

def get_statistics() -> Dict:
    """Get transcription statistics."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Total jobs
        cursor.execute('SELECT COUNT(*) FROM transcription_jobs')
        total = cursor.fetchone()[0]

        # Successful jobs
        cursor.execute("SELECT COUNT(*) FROM transcription_jobs WHERE status = 'completed'")
        successful = cursor.fetchone()[0]

        # Failed jobs
        cursor.execute("SELECT COUNT(*) FROM transcription_jobs WHERE status = 'failed'")
        failed = cursor.fetchone()[0]

        # Total audio minutes
        cursor.execute('SELECT COALESCE(SUM(duration_minutes), 0) FROM transcription_jobs')
        total_audio = cursor.fetchone()[0]

        # Total processing time
        cursor.execute('SELECT COALESCE(SUM(elapsed_seconds), 0) FROM transcription_jobs')
        total_processing = cursor.fetchone()[0] / 60  # Convert to minutes

        # Average speed (only successful jobs with speed > 0)
        cursor.execute('''
            SELECT COALESCE(AVG(speed), 0)
            FROM transcription_jobs
            WHERE status = 'completed' AND speed > 0
        ''')
        avg_speed = cursor.fetchone()[0]

        return {
            'total_jobs': total,
            'successful_jobs': successful,
            'failed_jobs': failed,
            'pending_jobs': total - successful - failed,
            'success_rate': (successful / total * 100) if total > 0 else 0,
            'total_audio_minutes': total_audio,
            'total_processing_minutes': total_processing,
            'average_speed': avg_speed
        }


# ==================== Settings ====================

def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        row = cursor.fetchone()
        if row:
            try:
                return json.loads(row[0])
            except:
                return row[0]
        return default


def set_setting(key: str, value: Any):
    """Set a setting value."""
    with get_connection() as conn:
        cursor = conn.cursor()
        value_str = json.dumps(value) if not isinstance(value, str) else value
        cursor.execute('''
            INSERT OR REPLACE INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        ''', (key, value_str))


def get_all_settings() -> Dict:
    """Get all settings."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT key, value FROM settings')
        settings = {}
        for row in cursor.fetchall():
            try:
                settings[row[0]] = json.loads(row[1])
            except:
                settings[row[0]] = row[1]
        return settings


# ==================== Migration from JSON ====================

def migrate_from_json(json_path: Path):
    """Migrate history from JSON file to SQLite."""
    if not json_path.exists():
        return 0

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            history = json.load(f)
    except:
        return 0

    migrated = 0
    with get_connection() as conn:
        cursor = conn.cursor()

        for entry in history:
            try:
                # Parse timestamp
                timestamp = entry.get('timestamp', '')
                created_at = datetime.fromisoformat(timestamp) if timestamp else datetime.now()

                cursor.execute('''
                    INSERT INTO transcription_jobs
                    (filename, output_path, duration_minutes, model,
                     elapsed_seconds, speed, status, created_at, completed_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entry.get('filename', 'Unknown'),
                    entry.get('output_path', ''),
                    entry.get('duration_minutes', 0),
                    entry.get('model', 'medium'),
                    entry.get('elapsed_seconds', 0),
                    entry.get('speed', 0),
                    'completed' if entry.get('success', False) else 'failed',
                    created_at,
                    created_at
                ))
                migrated += 1
            except Exception as e:
                print(f"Failed to migrate entry: {e}")
                continue

    return migrated


# Initialize database on import
init_database()
