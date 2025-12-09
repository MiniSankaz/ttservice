# KNOWN_ISSUES.md - Known Issues and Workarounds

> This file tracks known issues, limitations, and their workarounds.
> Check here first when encountering problems.

---

## Active Issues

*No active issues at this time. All known issues have been resolved.*

---

## Resolved Issues

### ISSUE-001: Thonburian Model Not Detected
**Status:** RESOLVED (2025-12-09)
**Symptom:** distill-thonburian-whisper-large-v3-mlx not showing in model list
**Cause:** Model uses `weights.safetensors` but code only checked for `weights.npz`
**Solution:** Updated `lib/models.py` to check both formats
**Commit:** 2a73f5b

---

### ISSUE-002: Hardcoded Paths in Tests
**Status:** RESOLVED (2025-12-09)
**Symptom:** Tests fail when project is in different location
**Cause:** Absolute paths hardcoded in `tests/rpa_web_test.py`
**Solution:** Changed to use `TestConfig` dataclass with dynamic paths
**Commit:** 2a73f5b

---

### ISSUE-003: 24-Worker Lock Contention
**Status:** RESOLVED (2025-12-08)
**Symptom:** 93% success rate with 24 workers, some chunks fail
**Cause:** Too many threads sharing one MLX model instance
**Solution:** Use Hybrid 2×8 architecture (2 processes, 8 workers each)
**Result:** 100% success rate

---

### ISSUE-004: Line 1472 Syntax Error
**Status:** RESOLVED (2025-12-09)
**Symptom:** Python syntax error with escaped quotes
**Cause:** Improper escaping of quotes in f-string
**Solution:** Changed outer quotes to double quotes, inner to single
**Before:** `'python -c "...snapshot_download(\\'repo\\'..."'`
**After:** `"python -c \"...snapshot_download('repo'...\""`

---

## Known Limitations

### LIM-001: macOS Only
**Description:** MLX requires Apple Silicon, so this project only runs on macOS M1/M2/M3/M4
**Workaround:** None - this is by design for Apple Silicon optimization
**Alternative:** Use standard Whisper with CUDA for other platforms

### LIM-002: Chrome Required for RPA Tests
**Description:** Selenium tests require Chrome browser and ChromeDriver
**Workaround:** Install Chrome, ChromeDriver is auto-downloaded by selenium
**Skip Tests:** Run with `--skip-transcription` for faster tests without Chrome

### LIM-003: Memory Usage with Large Models
**Description:** Large-v3 model uses ~2GB memory
**Workaround:** Use medium model for development (~0.5GB)
**Recommendation:** 16GB RAM minimum for large models

### LIM-004: Single User Only
**Description:** SQLite and local file storage are single-user
**Workaround:** None needed for intended use case
**Future:** Could add PostgreSQL support for multi-user

---

## Troubleshooting Guide

### Web UI Won't Start
```bash
# Check if port is in use
lsof -i :8501

# Kill existing process
./setup.sh --stop

# Restart
./setup.sh --start
```

### Model Download Fails
```bash
# Check internet connection
# Try manual download
python -c "from huggingface_hub import snapshot_download; snapshot_download('mlx-community/whisper-medium-mlx', local_dir='models/whisper-medium-mlx')"
```

### Transcription Hangs
- Check memory usage (Activity Monitor)
- Try smaller model
- Reduce workers in Settings > Performance

### Tests Fail
```bash
# Ensure server is running
./setup.sh --status

# Run with verbose output
python tests/rpa_web_test.py 2>&1 | tee test.log
```

---

## Issue Template

```markdown
### ISSUE-XXX: [Title]
**Status:** ACTIVE/RESOLVED
**Symptom:** [What the user sees]
**Cause:** [Root cause if known]
**Solution:** [How to fix]
**Workaround:** [Temporary fix if solution not yet available]
**Commit:** [Fix commit hash if resolved]
```
