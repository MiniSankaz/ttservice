# LLM Transcript Refinement - Executive Summary

**Date**: 2025-12-08
**Status**: Technical Analysis Complete
**Full Specification**: [llm-refinement-analysis.md](./llm-refinement-analysis.md)

---

## Quick Decision Summary

### Recommended Solution

**LLM**: MLX-LM with **Qwen2.5-7B-Instruct-4bit**
- Native Apple Silicon (Metal GPU)
- Excellent Thai language support
- 4GB memory footprint
- 20-30 tokens/sec on M2 Pro

**Architecture**: Post-processing Pipeline
```
Audio → Transcribe → Refine → Output
         (Whisper)   (LLM)
```

**Performance Target**: 2x realtime overall
- 120 min audio → 60 min total
- Transcription: 30 min (4x realtime)
- Refinement: 27 min (4.4x realtime)

---

## Why This Solution?

### 1. LLM Selection Rationale

| Criterion | Qwen2.5-7B | Score |
|-----------|------------|-------|
| Thai Language Quality | Excellent (multilingual training) | ⭐⭐⭐⭐⭐ |
| Apple Silicon Optimization | Native MLX | ⭐⭐⭐⭐⭐ |
| Memory Efficiency | 4GB (4-bit quantization) | ⭐⭐⭐⭐⭐ |
| Speed | 20-30 tokens/sec | ⭐⭐⭐⭐⭐ |
| Integration | Same framework as Whisper | ⭐⭐⭐⭐⭐ |

**Alternatives Considered**:
- Typhoon-7B (Thai-specific, but requires MLX conversion)
- Gemma-2-9B (good, but slightly larger/slower)
- Ollama + Llama3 (rejected: extra process overhead)

### 2. Architecture Rationale

**Post-Processing** (Sequential) vs Streaming (Parallel)

✅ **Chosen: Post-Processing**
- Simpler implementation
- Easier debugging
- Predictable performance
- No race conditions

❌ Rejected: Streaming
- More complex
- Harder to debug
- Better for future enhancement (Phase 5+)

---

## What It Does

### Refinement Tasks

1. **Add Punctuation** ⭐
   - Periods, commas, question marks
   - Thai-specific punctuation rules

2. **Paragraph Breaks** ⭐
   - Logical topic boundaries
   - 3-5 sentences per paragraph

3. **Fix Typos**
   - Context-aware corrections
   - Misheard words

4. **Format Consistency**
   - Spacing, quotes, numbers
   - Professional appearance

### Example

**Before (Raw Whisper)**:
```
สวัสดีครับวันนี้อากาศดีมากเลยนะครับผมชื่อสมชายครับวันนี้ผมจะมาพูดถึงเรื่องการใช้ AI ในการถอดเสียงครับ
```

**After (LLM Refined)**:
```
สวัสดีครับ วันนี้อากาศดีมากเลยนะครับ

ผมชื่อสมชายครับ วันนี้ผมจะมาพูดถึงเรื่องการใช้ AI ในการถอดเสียงครับ
```

---

## Performance Breakdown

### Time Estimate (120 min audio)

```
Stage                Time        % of Total
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Preprocessing        3 min       5%
Transcription       30 min      50%
Refinement ⭐       27 min      45%
Output              <1 min      <1%
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL               60 min     100%

Overall Speed: 2.0x realtime
```

### Memory Usage (Peak)

```
Component              Memory
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
System / macOS         3 GB
Whisper (2 instances)  2 GB
LLM Model (4-bit)      4 GB
Working Memory         2 GB
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TOTAL PEAK            11 GB

Safe for 16GB Mac ✅
```

---

## Implementation Roadmap

### Phase 1: Core Service (Week 1)
**Goal**: Basic refinement works

**Deliverables**:
- MLXLLMProcessor class
- Prompt templates (Thai + English)
- CLI script: `refine_transcript.py`
- Unit tests

**Usage**:
```bash
python scripts/refine_transcript.py \
    --input transcript.txt \
    --output refined.txt
```

### Phase 2: Chunking & Merging (Week 2)
**Goal**: Handle long transcripts

**Deliverables**:
- TextChunker class (paragraph-aware)
- ChunkMerger class (overlap detection)
- Support for 2+ hour transcripts
- Integration tests

**Features**:
- 80,000 char chunks
- 2,000 char overlap
- Smart paragraph splitting

### Phase 3: Pipeline Integration (Week 3)
**Goal**: Integrate with wizard

**Deliverables**:
- RefinementService class
- Wizard integration
- Progress tracking
- Error handling

**New Wizard Option**:
```
Refine transcript with LLM? (y/n): y
Model: [qwen2.5-7b] (or gemma, typhoon)
```

### Phase 4: Optimization (Week 4)
**Goal**: Performance & quality tuning

**Tasks**:
- Profile and optimize
- Test different prompts
- Model comparison (Qwen vs Typhoon vs Gemma)
- Quality benchmarks
- Documentation

---

## Technical Stack

### New Dependencies

```bash
# Add to requirements.txt
mlx-lm>=0.18.0         # MLX-LM for Apple Silicon
```

### New Modules

```
app/services/llm_refinement/
├── __init__.py
├── llm_processor.py        # MLX-LM wrapper
├── chunker.py              # Smart text chunking
├── merger.py               # Chunk merging
├── prompt_templates.py     # System prompts
└── refinement_service.py   # Main orchestrator
```

### New Scripts

```
scripts/
├── download_llm_models.py  # Download Qwen2.5-7B
└── refine_transcript.py    # CLI refinement tool
```

---

## Risk Mitigation

### Risk 1: LLM Hallucinates
**Impact**: High
**Mitigation**:
- Strict prompt engineering
- Validation (length change < 20%)
- User review workflow
- Fallback to raw transcript

### Risk 2: Out of Memory
**Impact**: High
**Mitigation**:
- Use 4-bit quantization (reduces to 4GB)
- Unload Whisper before loading LLM
- Sequential chunk processing
- Fallback to smaller model (3B)

### Risk 3: Slow Performance
**Impact**: Medium
**Mitigation**:
- Optimize chunk sizes
- Profile and tune
- Make refinement optional (flag: `--refine`)
- User can skip if too slow

### Risk 4: Quality Regression
**Impact**: High
**Mitigation**:
- Extensive testing (100+ samples)
- A/B comparison (raw vs refined)
- Quality metrics tracking
- Always save both raw and refined

---

## Success Criteria

### Go/No-Go Metrics

**Proceed if**:
- ✅ Overall speed ≥2x realtime
- ✅ Quality improvement visible
- ✅ Memory ≤12 GB peak
- ✅ Reliability ≥99%

**Reconsider if**:
- ❌ Speed <1.5x realtime
- ❌ No quality improvement
- ❌ Frequent OOM errors
- ❌ Model download issues

### Quality Targets

| Metric | Target |
|--------|--------|
| Punctuation Accuracy | ≥95% |
| Content Preservation | 100% |
| Paragraph Quality | ≥90% satisfaction |
| Typo Corrections | ≥80% correct |

---

## Installation & Setup

### Quick Start

```bash
# 1. Install dependencies
pip install mlx-lm>=0.18.0

# 2. Download LLM model (one-time, ~4GB)
python scripts/download_llm_models.py

# 3. Test basic refinement
python scripts/refine_transcript.py \
    --input sample_transcript.txt \
    --output refined.txt

# 4. Integrate with wizard
python transcribe_wizard.py --interactive
# → Select "Refine with LLM: Yes"
```

### System Requirements

**Minimum**:
- Apple Silicon Mac (M1+)
- 16 GB RAM
- 10 GB free storage
- macOS 12.0+

**Recommended**:
- M2 Pro or later
- 16 GB+ RAM
- 20 GB free storage
- Latest macOS

---

## Output Files

### Existing Outputs (Unchanged)
```
outputs/
├── meeting.txt         # Raw transcript
├── meeting.json        # Metadata + segments
└── meeting.srt         # Subtitles
```

### New Outputs (Added)
```
outputs/
├── meeting_refined.txt     # ⭐ LLM-refined transcript
├── meeting_refined.json    # ⭐ Refined + metadata
└── meeting_comparison.html # Optional: side-by-side diff
```

---

## Code Examples

### Basic Usage

```python
from app.services.llm_refinement import TranscriptRefinementService

# Initialize service
refiner = TranscriptRefinementService(
    model="mlx-community/Qwen2.5-7B-Instruct-4bit",
    language="th",
)

# Refine transcript
result = refiner.refine_transcript(
    transcript_file="transcript.txt",
    output_file="refined.txt",
)

print(f"Refined in {result['time_minutes']:.1f} minutes")
print(f"Output: {result['output_file']}")
```

### Integration with Wizard

```python
# In transcribe_wizard.py

# After transcription completes
if config.enable_refinement:
    from app.services.llm_refinement import TranscriptRefinementService

    refiner = TranscriptRefinementService(
        model=config.llm_model,
        language="th",
    )

    refined = refiner.refine_transcript(
        transcript_file=outputs["txt"],
        output_file=outputs["txt"].replace(".txt", "_refined.txt"),
    )

    print(f"✓ Refinement complete: {refined['output_file']}")
```

---

## Comparison with Alternatives

### vs Cloud APIs (GPT-4, Claude)

| Feature | Local LLM ⭐ | Cloud API |
|---------|-------------|-----------|
| **Cost** | Free (after setup) | $0.01-0.03 per 1K tokens |
| **Privacy** | 100% local | Data sent to cloud |
| **Speed** | 20-30 tok/sec | 30-50 tok/sec |
| **Quality** | Good (95%) | Excellent (98%) |
| **Offline** | ✅ Yes | ❌ Requires internet |
| **Setup** | 5 min | Immediate |

**Verdict**: Local LLM wins for privacy, cost, and offline capability

### vs Rule-Based Systems

| Feature | Local LLM ⭐ | Rule-Based |
|---------|-------------|------------|
| **Punctuation** | Excellent | Good |
| **Paragraphs** | Excellent | Poor |
| **Typo Fix** | Good | None |
| **Context-Aware** | ✅ Yes | ❌ No |
| **Thai Support** | Excellent | Poor |
| **Speed** | 20-30 tok/sec | 1000+ tok/sec |

**Verdict**: LLM much better quality, acceptable speed

---

## Next Actions

### For Development Planner
1. Read full specification: `docs/technical-specs/llm-refinement-analysis.md`
2. Create development tasks for Phases 1-4
3. Assign to appropriate developers
4. Schedule prototype demo (after Week 1)

### For Developers
1. Review code snippets in Appendix B of full spec
2. Install MLX-LM: `pip install mlx-lm>=0.18.0`
3. Download model: run `scripts/download_llm_models.py`
4. Start with Phase 1 implementation

### For QA/Testing
1. Prepare Thai transcript test set (10-20 samples)
2. Define quality evaluation criteria
3. Create benchmark suite
4. Plan A/B testing methodology

---

## Questions & Answers

**Q: Will this slow down my transcriptions?**
A: Total time increases by ~45%, but overall speed is still 2x realtime (120 min audio → 60 min total). Refinement is optional and can be disabled.

**Q: What if I don't have 16GB RAM?**
A: Use smaller model (Qwen2.5-3B-Instruct-4bit, ~2GB) or skip refinement. Whisper alone works fine with 8GB.

**Q: Does it work offline?**
A: Yes! After initial model download (~4GB), everything runs locally with no internet required.

**Q: Can I use a different model?**
A: Yes! See Section 3 of full spec for alternatives (Typhoon-7B, Gemma-2-9B). Easy to swap.

**Q: Will it change the meaning of my transcript?**
A: No. Strict validation ensures content preservation. Only formatting/punctuation changes. Original always saved.

**Q: How accurate is the refinement?**
A: Target: 95%+ punctuation accuracy. Quality depends on raw transcript quality. Always review critical documents.

---

## References

**Full Technical Specification**:
`/Volumes/DOWNLOAD/Docker Tools/transcriptor-pipeline-pilot/docs/technical-specs/llm-refinement-analysis.md`

**Key Sections**:
- Section 2: LLM Options Analysis
- Section 3: Model Selection (Thai language focus)
- Section 5: Architecture Design
- Section 7: Implementation Approach (4-week roadmap)
- Appendix B: Production-Ready Code

**External Resources**:
- MLX-LM: https://github.com/ml-explore/mlx-examples/tree/main/llms
- Qwen2.5: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- MLX Framework: https://github.com/ml-explore/mlx

---

**Document Version**: 1.0
**Last Updated**: 2025-12-08
**Status**: Ready for Implementation
