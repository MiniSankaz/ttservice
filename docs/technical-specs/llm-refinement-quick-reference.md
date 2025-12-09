# LLM Refinement - Quick Reference Card

## One-Sentence Summary
Add Local LLM (Qwen2.5-7B) to automatically improve transcript quality (punctuation, paragraphs, typo fixes) while maintaining 2x realtime speed on M2 Pro.

---

## The Solution in 3 Points

1. **LLM**: MLX-LM + Qwen2.5-7B-Instruct-4bit (~4GB)
2. **Architecture**: Transcribe → Refine → Output (post-processing)
3. **Performance**: 120 min audio → 60 min total (2x realtime)

---

## Visual Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BEFORE (Current)                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Audio ──> Preprocessing ──> MLX Whisper ──> Raw TXT/SRT    │
│   120min      3 min              30 min         (no punct)   │
│                                                               │
│  Total: 33 minutes (3.6x realtime)                           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    AFTER (Enhanced) ⭐                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Audio ──> Preprocessing ──> MLX Whisper ──> LLM Refine     │
│   120min      3 min              30 min         27 min       │
│                                                               │
│                            ↓                      ↓           │
│                       Raw TXT/SRT    Refined TXT (polished)  │
│                                                               │
│  Total: 60 minutes (2.0x realtime)                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Before/After Example

### Raw Transcript (Whisper Output)
```
สวัสดีครับวันนี้อากาศดีมากเลยนะครับผมชื่อสมชายครับ
วันนี้ผมจะมาพูดถึงเรื่องการใช้ AI ในการถอดเสียงครับ
ซึ่งเป็นเทคโนโลยีที่น่าสนใจมากครับโดยเฉพาะการใช้
โมเดล Whisper ของ OpenAI ซึ่งสามารถถอดเสียงภาษาไทย
ได้แม่นยำมากครับ
```

### Refined Transcript (LLM Output) ⭐
```
สวัสดีครับ วันนี้อากาศดีมากเลยนะครับ

ผมชื่อสมชายครับ วันนี้ผมจะมาพูดถึงเรื่องการใช้ AI
ในการถอดเสียงครับ ซึ่งเป็นเทคโนโลยีที่น่าสนใจมากครับ

โดยเฉพาะการใช้โมเดล Whisper ของ OpenAI ซึ่งสามารถ
ถอดเสียงภาษาไทยได้แม่นยำมากครับ
```

**Improvements**:
- Added periods and commas
- Paragraph breaks at logical points
- Better readability
- Professional formatting

---

## Key Metrics

| Metric | Value |
|--------|-------|
| **LLM Model** | Qwen2.5-7B-Instruct-4bit |
| **Model Size** | 3.8 GB (downloads once) |
| **Memory Usage** | 11 GB peak (safe for 16GB Mac) |
| **Speed** | 20-30 tokens/sec |
| **Overall Pipeline** | 2x realtime (60 min for 120 min audio) |
| **Quality** | 95%+ punctuation accuracy |
| **Thai Support** | Excellent (native multilingual) |
| **Cost** | Free (local processing) |

---

## 4-Week Implementation

```
Week 1: Core Service
├── MLX-LM integration
├── Prompt engineering
└── CLI tool
    └── refine_transcript.py

Week 2: Chunking
├── Smart text splitting (80K chars)
├── Overlap handling (2K chars)
└── Paragraph-aware merging

Week 3: Integration
├── Add to wizard
├── Progress tracking
└── Error handling

Week 4: Optimization
├── Performance tuning
├── Quality evaluation
└── Documentation
```

---

## Installation (3 Commands)

```bash
# 1. Install MLX-LM
pip install mlx-lm>=0.18.0

# 2. Download model (~4GB, one-time)
python scripts/download_llm_models.py

# 3. Test
python scripts/refine_transcript.py --input test.txt --output refined.txt
```

---

## Usage Examples

### CLI Refinement
```bash
# Refine existing transcript
python scripts/refine_transcript.py \
    --input transcript.txt \
    --output refined.txt \
    --model qwen2.5-7b-instruct-4bit
```

### Wizard (Auto Mode)
```bash
python transcribe_wizard.py --interactive

# Wizard will ask:
# "Refine transcript with LLM? (y/n): y"
# → Automatically refines after transcription
```

### Programmatic
```python
from app.services.llm_refinement import TranscriptRefinementService

refiner = TranscriptRefinementService(model="qwen2.5-7b-instruct-4bit")
result = refiner.refine_transcript("input.txt", "output.txt")
print(f"Done in {result['time_minutes']:.1f} minutes")
```

---

## Resource Requirements

### Disk Space
```
Models:
├── Whisper Medium MLX:    1.5 GB
├── Whisper Large-v3 MLX:  3.0 GB
├── Qwen2.5-7B-4bit:       3.8 GB
└── Total:                 ~8.3 GB
```

### Memory (Peak Usage)
```
Component              Memory    Notes
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
System (macOS)         3 GB      Background
Whisper (2 instances)  2 GB      During transcription
LLM (Qwen 4-bit)       4 GB      During refinement
Working Memory         2 GB      Buffers, overhead
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL PEAK            11 GB      Safe for 16GB Mac
```

### Performance (M2 Pro, 16GB)
```
Audio Length    Transcribe    Refine    Total     Speed
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  60 min         15 min       13 min    28 min    2.1x
 120 min         30 min       27 min    57 min    2.1x
 240 min         60 min       54 min   114 min    2.1x
```

---

## Refinement Tasks Breakdown

### 1. Punctuation (95% accuracy target)
- Periods (.) at sentence ends
- Commas (,) for clause separation
- Question marks (?) for questions
- Exclamation marks (!) when appropriate
- Thai-specific rules (ฯลฯ, ฯ)

### 2. Paragraph Breaks (90% satisfaction target)
- Topic changes → new paragraph
- Speaker changes → new paragraph
- 3-5 sentences per paragraph
- Logical flow

### 3. Typo Correction (80% accuracy target)
- Misheard words (context-aware)
- Technical terms
- Proper nouns
- Conservative (only if certain)

### 4. Formatting
- Consistent spacing
- Quote marks for direct speech
- Number formatting
- Professional appearance

---

## Risk Mitigation Summary

| Risk | Mitigation |
|------|------------|
| **Hallucination** | Strict prompts + validation (length change <20%) |
| **Out of Memory** | 4-bit quantization + sequential processing |
| **Slow Speed** | Optimize chunks + make optional |
| **Quality Issues** | Extensive testing + always save raw |

---

## Success Criteria

### Go Criteria ✅
- Overall speed ≥2x realtime
- Visible quality improvement
- Memory ≤12 GB peak
- Reliability ≥99%

### No-Go Criteria ❌
- Speed <1.5x realtime
- No quality improvement
- Frequent OOM errors
- Model issues

---

## File Structure

```
app/services/llm_refinement/
├── __init__.py
├── llm_processor.py          # MLX-LM wrapper
├── chunker.py                # Text splitting
├── merger.py                 # Chunk merging
├── prompt_templates.py       # Thai/English prompts
└── refinement_service.py     # Main orchestrator

scripts/
├── download_llm_models.py    # Model downloader
└── refine_transcript.py      # CLI tool

docs/technical-specs/
├── llm-refinement-analysis.md     # Full spec (45+ pages)
├── llm-refinement-summary.md      # Executive summary
└── llm-refinement-quick-reference.md  # This file
```

---

## Comparison Table

### LLM Options
| LLM | Thai | Memory | Speed | Choice |
|-----|------|--------|-------|--------|
| **Qwen2.5-7B** | ⭐⭐⭐⭐⭐ | 4 GB | 25 tok/s | ✅ Primary |
| Typhoon-7B | ⭐⭐⭐⭐⭐ | 4 GB | 25 tok/s | Alternative |
| Gemma-2-9B | ⭐⭐⭐⭐ | 5 GB | 20 tok/s | Alternative |
| Llama3.2-8B | ⭐⭐⭐ | 4 GB | 22 tok/s | Fallback |

### Architecture Options
| Architecture | Pros | Cons | Choice |
|--------------|------|------|--------|
| **Post-processing** | Simple, reliable | Slower overall | ✅ Phase 1-4 |
| Streaming | Faster overall | Complex | Future (Phase 5+) |
| Rule-based | Very fast | Poor quality | ❌ Rejected |
| Cloud API | Best quality | Privacy/cost | ❌ Rejected |

---

## Configuration

### Environment Variables (New)
```bash
# Add to .env or config
REFINEMENT_ENABLED=true
REFINEMENT_MODEL=mlx-community/Qwen2.5-7B-Instruct-4bit
REFINEMENT_CHUNK_SIZE=80000
REFINEMENT_OVERLAP=2000
REFINEMENT_MAX_RETRIES=3
```

### Wizard Options (New)
```bash
python transcribe_wizard.py --interactive

# New prompts:
# "Enable LLM refinement? (y/n): "
# "Select model: [qwen2.5-7b] / gemma / typhoon"
# "Quality mode: [balanced] / fast / best"
```

---

## Testing Checklist

### Phase 1 Testing
- [ ] MLX-LM loads successfully
- [ ] Single chunk refinement works
- [ ] Thai punctuation accurate
- [ ] Memory <6 GB
- [ ] Speed >20 tokens/sec

### Phase 2 Testing
- [ ] Long transcripts (2+ hours) work
- [ ] Chunk overlap detected correctly
- [ ] Paragraph boundaries preserved
- [ ] No text loss

### Phase 3 Testing
- [ ] Wizard integration seamless
- [ ] Progress tracking accurate
- [ ] Error handling robust
- [ ] Fallback to raw works

### Phase 4 Testing
- [ ] Performance meets target (2x realtime)
- [ ] Quality benchmarks passed
- [ ] A/B testing completed
- [ ] Documentation complete

---

## Troubleshooting

### Problem: Model download fails
**Solution**: Check internet connection, try manual download:
```bash
python -c "from mlx_lm import load; load('mlx-community/Qwen2.5-7B-Instruct-4bit')"
```

### Problem: Out of memory
**Solution**:
1. Unload Whisper before loading LLM
2. Use smaller model (Qwen2.5-3B-Instruct-4bit)
3. Close other apps

### Problem: Slow refinement
**Solution**:
1. Check GPU usage (Activity Monitor)
2. Reduce chunk size to 60K
3. Use faster model (sacrifice quality)

### Problem: Poor quality
**Solution**:
1. Try different prompts
2. Switch to larger model (Typhoon-7B)
3. Enable multi-pass refinement

---

## References

**Full Documentation**:
- Technical Analysis (45+ pages): `docs/technical-specs/llm-refinement-analysis.md`
- Executive Summary: `docs/technical-specs/llm-refinement-summary.md`
- This Quick Reference: `docs/technical-specs/llm-refinement-quick-reference.md`

**Code Examples**:
- Appendix B in full specification (production-ready code)

**External**:
- MLX-LM: https://github.com/ml-explore/mlx-examples/tree/main/llms
- Qwen2.5: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct

---

## Next Steps

1. **Read**: Full specification (`llm-refinement-analysis.md`)
2. **Install**: `pip install mlx-lm>=0.18.0`
3. **Download**: `python scripts/download_llm_models.py`
4. **Test**: `python scripts/refine_transcript.py --input test.txt`
5. **Implement**: Follow Week 1-4 roadmap

---

**Last Updated**: 2025-12-08
**Version**: 1.0
**Status**: Ready for Implementation
