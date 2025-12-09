# Technical Analysis: Local LLM Transcript Refinement

**Date**: 2025-12-08
**Author**: System Analyst Agent
**Project**: Transcriptor Pipeline Pilot
**Feature**: Local LLM-based Transcript Refinement

---

## Executive Summary

This document provides a comprehensive technical analysis for adding Local LLM-based transcript refinement to the Transcriptor Pipeline. The analysis covers LLM selection, architecture design, performance optimization, and implementation strategy specifically optimized for Apple Silicon (M2 Pro, 16GB RAM) with strong Thai language support.

**Key Recommendations**:
- **Primary LLM**: MLX-LM with Qwen2.5-7B-Instruct-MLX
- **Architecture**: Post-processing pipeline with chunk-based streaming
- **Performance Target**: 2-4x realtime (120 min audio → 30-60 min refinement)
- **Memory Usage**: ~4-6 GB (MLX model loading)

---

## Table of Contents

1. [Current System Analysis](#1-current-system-analysis)
2. [Local LLM Options Analysis](#2-local-llm-options-analysis)
3. [Model Selection for Thai Language](#3-model-selection-for-thai-language)
4. [Refinement Strategy](#4-refinement-strategy)
5. [Architecture Design](#5-architecture-design)
6. [Performance Analysis](#6-performance-analysis)
7. [Implementation Approach](#7-implementation-approach)
8. [Integration with Existing Pipeline](#8-integration-with-existing-pipeline)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment Considerations](#10-deployment-considerations)

---

## 1. Current System Analysis

### 1.1 Existing Architecture

```
Current Transcriptor Pipeline:
┌────────────────────────────────────────────────────────┐
│  INPUT: Audio File (MP3, WAV, M4A, etc.)              │
└────────────────┬───────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│  PREPROCESSING (CPU-bound)                             │
│  • Noise reduction                                     │
│  • Audio normalization                                 │
│  • Smart chunking (20s chunks, 3s overlap)            │
└────────────────┬───────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│  TRANSCRIPTION (MLX GPU-accelerated)                   │
│  • Hybrid 2×8: 2 processes × 8 workers                │
│  • MLX Whisper Medium/Large-v3                        │
│  • Performance: 3.2-4x realtime                       │
└────────────────┬───────────────────────────────────────┘
                 │
                 ▼
┌────────────────────────────────────────────────────────┐
│  OUTPUT: TXT, JSON, SRT                               │
│  • Raw transcription                                   │
│  • Timestamp segments                                  │
│  • Metadata                                            │
└────────────────────────────────────────────────────────┘
```

### 1.2 Current System Specifications

| Component | Details |
|-----------|---------|
| **Hardware** | Apple Silicon M2 Pro, 16GB RAM |
| **Transcription** | MLX Whisper (Medium: ~0.5GB, Large-v3: ~1.5GB per instance) |
| **Performance** | 74 min audio → 18.7 min (medium, 2×8), 3.98x realtime |
| **Memory Usage** | 1-2 GB for 2 model instances |
| **Languages** | Thai (primary), English, Chinese, Japanese, Korean |
| **Output Formats** | TXT, JSON, SRT |

### 1.3 Current Challenges

Raw Whisper transcriptions often have:
- **Missing punctuation** (especially in Thai)
- **No paragraph breaks**
- **Misheard words** (especially technical terms, names)
- **Inconsistent formatting**
- **No context-aware corrections**

---

## 2. Local LLM Options Analysis

### 2.1 LLM Runtime Options for Apple Silicon

| Option | Pros | Cons | Thai Support | Performance |
|--------|------|------|--------------|-------------|
| **MLX-LM** ⭐ | • Native Apple Silicon (Metal)<br>• Memory efficient<br>• Fast inference<br>• Python-native API<br>• Active development | • Limited model selection<br>• Requires MLX conversion | ✅ Excellent (Qwen, Gemma) | ⭐⭐⭐⭐⭐ |
| **Ollama** | • Easy model management<br>• REST API<br>• Large model library<br>• Good documentation | • Higher memory overhead<br>• Additional process<br>• Network latency | ✅ Good (Llama3, Qwen) | ⭐⭐⭐⭐ |
| **llama.cpp** | • Very efficient<br>• Wide model support<br>• Quantization options | • C++ binding complexity<br>• Less Pythonic<br>• Manual setup | ✅ Good | ⭐⭐⭐⭐ |
| **LM Studio** | • GUI management<br>• Easy setup | • GUI dependency<br>• No programmatic API | ✅ Good | ⭐⭐⭐ |

### 2.2 Recommended Option: MLX-LM

**Rationale**:
1. **Native Integration**: Already using MLX framework for Whisper
2. **Memory Efficiency**: Shared Metal GPU memory with Whisper
3. **Performance**: Optimized for Apple Silicon Neural Engine
4. **Python-Native**: Easy integration with existing codebase
5. **Low Latency**: In-process inference (no IPC overhead)

**Installation**:
```bash
pip install mlx-lm>=0.18.0
```

---

## 3. Model Selection for Thai Language

### 3.1 Model Comparison for Thai Support

| Model | Size | Thai Quality | Speed (16GB RAM) | Memory | Recommendation |
|-------|------|--------------|------------------|--------|----------------|
| **Qwen2.5-7B-Instruct** ⭐ | 7B | ⭐⭐⭐⭐⭐ | ~20 tokens/sec | 4-5 GB | **Primary** |
| **Gemma-2-9B-Instruct** | 9B | ⭐⭐⭐⭐ | ~15 tokens/sec | 5-6 GB | Secondary |
| **Llama-3.2-8B-Instruct** | 8B | ⭐⭐⭐ | ~18 tokens/sec | 4-5 GB | Fallback |
| **Typhoon-7B** | 7B | ⭐⭐⭐⭐⭐ | ~20 tokens/sec | 4-5 GB | Thai-specific |
| **SeaLLM-7B** | 7B | ⭐⭐⭐⭐ | ~20 tokens/sec | 4-5 GB | SEA languages |

### 3.2 Recommended Primary Model: Qwen2.5-7B-Instruct-MLX

**Model**: `mlx-community/Qwen2.5-7B-Instruct-4bit`

**Strengths**:
- ✅ **Excellent Thai language understanding** (trained on multilingual data)
- ✅ **Instruction-following** (tuned for tasks like refinement)
- ✅ **4-bit quantization** (reduces memory to ~4GB)
- ✅ **Fast inference** (~20-30 tokens/sec on M2 Pro)
- ✅ **Context window**: 32K tokens (enough for long chunks)

**Performance Estimates** (M2 Pro, 16GB RAM):
- **Throughput**: 20-30 tokens/sec
- **Latency**: 1-2 seconds per 1000 characters
- **Memory**: ~4GB model + ~1GB working memory
- **Total**: ~5-6GB peak

### 3.3 Alternative: Typhoon-7B (Thai-Specific)

**Model**: `scb10x/typhoon-7b` (requires MLX conversion)

**Strengths**:
- ✅ **Specifically trained for Thai** by SCB10X
- ✅ **Excellent Thai grammar and context**
- ✅ **Local Thai cultural knowledge**

**Limitations**:
- ⚠️ Requires manual MLX conversion
- ⚠️ Less frequent updates
- ⚠️ Smaller community

**Recommendation**: Use as secondary option if Qwen2.5 doesn't meet quality requirements.

---

## 4. Refinement Strategy

### 4.1 Refinement Tasks

```python
REFINEMENT_TASKS = {
    "punctuation": {
        "priority": 1,
        "description": "Add periods, commas, question marks, exclamation marks",
        "thai_specific": True,  # Thai uses different punctuation rules
    },
    "paragraphs": {
        "priority": 2,
        "description": "Break text into logical paragraphs by topic/speaker",
        "chunking": True,
    },
    "typo_correction": {
        "priority": 3,
        "description": "Fix misheard words using context",
        "context_aware": True,
    },
    "formatting": {
        "priority": 4,
        "description": "Consistent spacing, quotes, numbers",
    },
    "capitalization": {
        "priority": 5,
        "description": "Proper names, acronyms (Thai has less capitalization)",
        "thai_specific": True,
    },
}
```

### 4.2 Prompt Engineering Strategy

#### System Prompt Template
```python
SYSTEM_PROMPT_TH = """คุณเป็นผู้เชี่ยวชาญในการปรับปรุงข้อความที่ถอดเสียงจาก AI speech-to-text

งานของคุณ:
1. เพิ่มเครื่องหมายวรรคตอน (. , ? ! ฯลฯ)
2. แบ่งย่อหน้าตามหัวข้อที่สมเหตุสมผล
3. แก้คำที่อาจจะได้ยินผิดโดยใช้บริบทโดยรอบ
4. จัดรูปแบบให้สม่ำเสมอ (ช่องว่าง เครื่องหมายคำพูด ตัวเลข)

ข้อกำหนด:
- รักษาเนื้อหาเดิมไว้ ห้ามเพิ่มข้อมูลใหม่
- ห้ามสรุปหรือตัดทอน
- ใช้ภาษาไทยมาตรฐาน
- เมื่อไม่แน่ใจ ให้ใช้ข้อความเดิม
- ตอบกลับเฉพาะข้อความที่ปรับปรุงแล้ว ไม่ต้องอธิบายเพิ่มเติม
"""

USER_PROMPT_TEMPLATE = """ปรับปรุงข้อความที่ถอดเสียงนี้:

{transcript}

ข้อความที่ปรับปรุงแล้ว:"""
```

#### Multi-Pass Strategy (Optional)
```python
MULTI_PASS_PROMPTS = {
    "pass_1_punctuation": "เพิ่มเครื่องหมายวรรคตอนเท่านั้น",
    "pass_2_paragraphs": "แบ่งย่อหน้า",
    "pass_3_corrections": "แก้ไขคำผิดด้วยบริบท",
}
```

**Trade-off**:
- **Single-pass**: Faster (1x), slightly lower quality
- **Multi-pass**: 3x slower, higher quality
- **Recommendation**: Start with single-pass, add multi-pass as optional flag

### 4.3 Chunking Strategy for LLM

#### Chunk Size Calculation
```python
# LLM Context Window: 32K tokens
# Reserve for prompt: ~500 tokens
# Reserve for response: ~2000 tokens
# Available for transcript: ~29,500 tokens

# Thai text: ~1.5 tokens per word, ~4 chars per token
MAX_CHUNK_SIZE = 29_500 * 4  # ~118,000 characters per chunk

# Conservative safe limit
RECOMMENDED_CHUNK_SIZE = 80_000  # characters (~20,000 tokens)
```

#### Overlap Strategy
```python
CHUNK_CONFIG = {
    "max_chars": 80_000,
    "overlap_chars": 2_000,  # ~500 words overlap
    "split_strategy": "paragraph_aware",  # Don't split mid-paragraph
}
```

### 4.4 Context Preservation

For long transcripts (>80K chars):
1. **Split into chunks** with overlap
2. **Preserve context** by including last 2 paragraphs from previous chunk
3. **Merge smartly** by detecting and removing duplicate overlapping sections

---

## 5. Architecture Design

### 5.1 System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENHANCED PIPELINE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌───────────────────────────────────────────────────────┐    │
│   │  STAGE 1: PREPROCESSING (Existing)                    │    │
│   │  • Noise reduction                                     │    │
│   │  • Audio chunking                                      │    │
│   └────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│                             ▼                                    │
│   ┌───────────────────────────────────────────────────────┐    │
│   │  STAGE 2: TRANSCRIPTION (Existing)                    │    │
│   │  • MLX Whisper                                        │    │
│   │  • Hybrid 2×8 workers                                 │    │
│   │  • Output: Raw transcript                             │    │
│   └────────────────────────┬──────────────────────────────┘    │
│                             │                                    │
│                             ▼                                    │
│   ┌───────────────────────────────────────────────────────┐    │
│   │  STAGE 3: REFINEMENT (NEW) ⭐                         │    │
│   │  ┌─────────────────────────────────────────────────┐ │    │
│   │  │  Text Chunker (Paragraph-aware)                 │ │    │
│   │  │  • Split into ~80K char chunks                   │ │    │
│   │  │  • 2K char overlap                               │ │    │
│   │  └────────────┬────────────────────────────────────┘ │    │
│   │               │                                        │    │
│   │               ▼                                        │    │
│   │  ┌─────────────────────────────────────────────────┐ │    │
│   │  │  LLM Processor (Streaming)                      │ │    │
│   │  │  • MLX-LM + Qwen2.5-7B-Instruct-4bit           │ │    │
│   │  │  • Batch processing                             │ │    │
│   │  │  • Progress tracking                            │ │    │
│   │  └────────────┬────────────────────────────────────┘ │    │
│   │               │                                        │    │
│   │               ▼                                        │    │
│   │  ┌─────────────────────────────────────────────────┐ │    │
│   │  │  Chunk Merger                                   │ │    │
│   │  │  • Smart overlap detection                      │ │    │
│   │  │  • Paragraph preservation                       │ │    │
│   │  └────────────┬────────────────────────────────────┘ │    │
│   │               │                                        │    │
│   └───────────────┼────────────────────────────────────────┘    │
│                   │                                              │
│                   ▼                                              │
│   ┌───────────────────────────────────────────────────────┐    │
│   │  STAGE 4: OUTPUT                                      │    │
│   │  • Raw transcript (TXT, JSON, SRT) - Existing         │    │
│   │  • Refined transcript (TXT, JSON) - NEW ⭐           │    │
│   │  • Diff/comparison (optional)                         │    │
│   └───────────────────────────────────────────────────────┘    │
│                                                                   │
└───────────────────────────────────────────────────────────────┘
```

### 5.2 Module Structure

```
app/services/llm_refinement/
├── __init__.py
├── chunker.py              # Smart text chunking
├── llm_processor.py        # MLX-LM wrapper
├── prompt_templates.py     # System/user prompts
├── merger.py               # Chunk result merging
└── refinement_service.py   # Main orchestrator
```

### 5.3 Data Flow

```python
# Input
raw_transcript = {
    "text": "ข้อความทั้งหมด...",
    "segments": [...],  # With timestamps
}

# Step 1: Chunk
chunks = chunker.split_text(
    raw_transcript["text"],
    max_chars=80_000,
    overlap=2_000,
)

# Step 2: Process each chunk
refined_chunks = []
for chunk in chunks:
    refined = llm_processor.refine(
        chunk_text=chunk,
        prompt_template=SYSTEM_PROMPT_TH,
    )
    refined_chunks.append(refined)

# Step 3: Merge
refined_text = merger.merge_chunks(
    chunks=refined_chunks,
    overlap_chars=2_000,
)

# Output
refined_transcript = {
    "text": refined_text,
    "original_text": raw_transcript["text"],
    "segments": raw_transcript["segments"],  # Preserve timestamps
    "metadata": {
        "model": "qwen2.5-7b-instruct-4bit",
        "chunks_processed": len(chunks),
        "refinement_time": elapsed_time,
    }
}
```

### 5.4 Processing Modes

#### Mode 1: Sequential (Default)
```python
# Transcribe → Refine
transcribe() → refine()
```
- Simple, predictable
- Total time = transcribe_time + refine_time

#### Mode 2: Streaming (Advanced)
```python
# Refine chunks as they're transcribed
transcribe_chunk() → refine_chunk() (overlapped)
```
- Faster overall
- More complex
- Recommendation: Implement Mode 1 first, add Mode 2 later

---

## 6. Performance Analysis

### 6.1 Performance Estimates

#### Transcription Stage (Existing)
| Audio Length | Model | Time | Speed |
|--------------|-------|------|-------|
| 120 min | medium | 30 min | 4x realtime |
| 120 min | large-v3 | 67 min | 1.8x realtime |

#### Refinement Stage (Estimated)

**Assumptions**:
- LLM: Qwen2.5-7B-Instruct-4bit
- Hardware: M2 Pro, 16GB RAM
- Throughput: 25 tokens/sec (conservative)
- Thai text: ~4 chars per token

**Calculation**:
```python
# Example: 120 min audio transcription
raw_transcript_length = 150_000  # characters (~2.5 hours talking)

# Chunking
chunk_size = 80_000
num_chunks = ceil(150_000 / 78_000)  # With overlap
# num_chunks = 2

# LLM processing per chunk
chars_per_chunk = 80_000
tokens_per_chunk = 80_000 / 4  # = 20,000 tokens
throughput = 25  # tokens/sec
time_per_chunk = 20_000 / 25  # = 800 seconds = 13.3 min

# Total refinement time
total_chunks = 2
total_refinement = 2 × 13.3 = 26.6 minutes

# Total pipeline
total_time = transcription(30 min) + refinement(26.6 min)
           = 56.6 minutes
```

#### Performance Summary

| Audio Length | Transcription | Refinement | Total | Overall Speed |
|--------------|---------------|------------|-------|---------------|
| 60 min | 15 min | 13 min | 28 min | 2.1x realtime |
| 120 min | 30 min | 27 min | 57 min | 2.1x realtime |
| 240 min | 60 min | 54 min | 114 min | 2.1x realtime |

**Overall Speed**: ~2x realtime (with refinement)

### 6.2 Memory Requirements

```
Memory Breakdown (Peak):
┌────────────────────────────────┐
│ Component            Memory    │
├────────────────────────────────┤
│ System / macOS       3 GB      │
│ Whisper (2 instances) 2 GB     │
│ LLM Model (4-bit)    4 GB      │
│ Working Memory       1 GB      │
│ Buffer               1 GB      │
├────────────────────────────────┤
│ Total Peak           11 GB     │
└────────────────────────────────┘

Available on 16GB Mac: 11 GB (safe)
```

**Optimization Strategy**:
- **Unload Whisper** before loading LLM (if needed)
- **Use 4-bit quantization** for LLM
- **Process chunks sequentially** (avoid loading multiple chunks)

### 6.3 Bottleneck Analysis

| Stage | Bottleneck | Mitigation |
|-------|------------|------------|
| **Transcription** | GPU/Neural Engine | Already optimized (MLX) |
| **Refinement** | LLM token generation | • Use 4-bit quantization<br>• Batch small chunks<br>• Consider streaming |
| **Disk I/O** | Reading/writing files | Minimal impact |
| **Memory** | 16GB total | Sequential processing, unload models |

---

## 7. Implementation Approach

### 7.1 Phase 1: Core Refinement Service (Week 1)

**Objectives**:
- Implement basic LLM refinement
- Single-pass, single chunk support
- CLI interface

**Components**:
1. **LLM Processor** (`llm_processor.py`)
   ```python
   class MLXLLMProcessor:
       def __init__(self, model_name: str, quantization: str = "4bit"):
           self.model = load_mlx_model(model_name)

       def refine_text(self, text: str, prompt: str) -> str:
           # Generate refined text
           pass
   ```

2. **Prompt Templates** (`prompt_templates.py`)
   ```python
   SYSTEM_PROMPTS = {
       "th": SYSTEM_PROMPT_TH,
       "en": SYSTEM_PROMPT_EN,
   }
   ```

3. **CLI Script** (`scripts/refine_transcript.py`)
   ```bash
   python scripts/refine_transcript.py \
       --input transcript.txt \
       --output refined.txt \
       --model qwen2.5-7b-instruct-4bit
   ```

**Deliverables**:
- ✅ Basic refinement works end-to-end
- ✅ CLI interface
- ✅ Unit tests

### 7.2 Phase 2: Chunking & Merging (Week 2)

**Objectives**:
- Support long transcripts (>80K chars)
- Smart paragraph-aware chunking
- Overlap detection and merging

**Components**:
1. **Chunker** (`chunker.py`)
   ```python
   class TextChunker:
       def split_text(
           self,
           text: str,
           max_chars: int = 80_000,
           overlap: int = 2_000,
       ) -> List[Chunk]:
           # Smart splitting logic
           pass
   ```

2. **Merger** (`merger.py`)
   ```python
   class ChunkMerger:
       def merge_chunks(
           self,
           refined_chunks: List[str],
           overlap_chars: int = 2_000,
       ) -> str:
           # Detect and remove overlaps
           pass
   ```

**Deliverables**:
- ✅ Handles 2-hour transcripts (~150K chars)
- ✅ No information loss in merging
- ✅ Integration tests

### 7.3 Phase 3: Integration with Pipeline (Week 3)

**Objectives**:
- Integrate refinement into main pipeline
- Add to wizard
- Progress tracking

**Components**:
1. **Refinement Service** (`refinement_service.py`)
   ```python
   class TranscriptRefinementService:
       def refine_transcript(
           self,
           transcript_file: str,
           output_file: str,
           model: str = "qwen2.5-7b-instruct-4bit",
           progress_callback: Optional[Callable] = None,
       ) -> Dict[str, Any]:
           # Orchestrate chunking → LLM → merging
           pass
   ```

2. **Wizard Integration** (`transcribe_wizard.py`)
   ```python
   # Add option to wizard
   refine_option = input("Refine transcript with LLM? (y/n): ")
   if refine_option.lower() == 'y':
       refine_transcript(...)
   ```

**Deliverables**:
- ✅ End-to-end pipeline works
- ✅ Progress bars / logging
- ✅ Error handling

### 7.4 Phase 4: Optimization & Quality (Week 4)

**Objectives**:
- Optimize performance
- Quality improvements
- Model comparison

**Tasks**:
1. **Performance Optimization**
   - Profile LLM inference
   - Tune chunk sizes
   - Implement batch processing (if beneficial)

2. **Quality Improvements**
   - Test different prompts
   - Add multi-pass option
   - Create quality evaluation dataset

3. **Model Comparison**
   - Test Qwen2.5 vs Typhoon vs Gemma
   - Document quality/speed trade-offs

**Deliverables**:
- ✅ 2x realtime overall speed maintained
- ✅ Quality benchmarks documented
- ✅ Model selection guide

---

## 8. Integration with Existing Pipeline

### 8.1 Modification Points

#### 1. Add Refinement to Wizard (`transcribe_wizard.py`)
```python
# After transcription completes
if config.enable_refinement:
    logger.info("Starting LLM refinement...")
    refiner = TranscriptRefinementService(
        model=config.llm_model,
        language=config.language,
    )

    refined_result = refiner.refine_transcript(
        transcript_file=transcript_output["text_file"],
        output_file=transcript_output["text_file"].replace(".txt", "_refined.txt"),
    )

    logger.info(f"Refinement complete: {refined_result['output_file']}")
```

#### 2. Update Output Files
```python
# Existing outputs
outputs = {
    "raw": {
        "txt": "transcript.txt",
        "json": "transcript.json",
        "srt": "transcript.srt",
    },
    "refined": {
        "txt": "transcript_refined.txt",
        "json": "transcript_refined.json",
        # No SRT for refined (timestamps may not align)
    },
    "comparison": {
        "diff": "transcript_comparison.html",  # Optional
    }
}
```

#### 3. Configuration Options
```python
# Add to wizard config
REFINEMENT_CONFIG = {
    "enable_refinement": True,  # Master switch
    "llm_model": "qwen2.5-7b-instruct-4bit",
    "chunk_size": 80_000,
    "chunk_overlap": 2_000,
    "max_retries": 3,
    "fallback_to_raw": True,  # If refinement fails
}
```

### 8.2 Backward Compatibility

- ✅ Refinement is **optional** (default: disabled)
- ✅ Raw transcripts always saved
- ✅ Existing scripts continue to work
- ✅ CLI flag to enable: `--refine` or `--no-refine`

### 8.3 Error Handling

```python
try:
    refined = refiner.refine_transcript(...)
except OutOfMemoryError:
    logger.warning("OOM during refinement, falling back to raw transcript")
    return {"status": "fallback", "file": raw_transcript}
except LLMModelNotFoundError:
    logger.error("LLM model not found, skipping refinement")
    return {"status": "skipped", "file": raw_transcript}
```

---

## 9. Testing Strategy

### 9.1 Unit Tests

```python
# tests/test_llm_refinement.py
def test_chunker_basic():
    """Test text chunker creates chunks within size limits"""
    chunker = TextChunker(max_chars=1000, overlap=100)
    text = "a" * 5000
    chunks = chunker.split_text(text)

    assert len(chunks) >= 5
    assert all(len(c) <= 1000 for c in chunks)

def test_merger_removes_overlap():
    """Test merger correctly removes overlapping text"""
    merger = ChunkMerger()
    chunks = [
        "Hello world this is a test",
        "a test of the system",
    ]
    merged = merger.merge_chunks(chunks, overlap_chars=10)

    assert "a test" in merged
    assert merged.count("a test") == 1  # No duplication

def test_llm_processor_thai():
    """Test LLM processes Thai text correctly"""
    processor = MLXLLMProcessor(model="qwen2.5-7b-instruct-4bit")
    raw = "สวัสดีครับวันนี้อากาศดีมากเลยนะครับ"
    refined = processor.refine_text(raw, SYSTEM_PROMPT_TH)

    assert "สวัสดีครับ" in refined
    assert len(refined) > 0
```

### 9.2 Integration Tests

```python
def test_end_to_end_refinement():
    """Test complete refinement pipeline"""
    service = TranscriptRefinementService(model="qwen2.5-7b-instruct-4bit")

    # Create test transcript
    test_transcript = Path("tests/fixtures/sample_transcript.txt")
    output_file = Path("/tmp/refined_output.txt")

    result = service.refine_transcript(
        transcript_file=str(test_transcript),
        output_file=str(output_file),
    )

    assert result["status"] == "success"
    assert output_file.exists()
    assert output_file.stat().st_size > 0
```

### 9.3 Quality Evaluation

Create test set with ground truth:
```python
TEST_CASES = [
    {
        "raw": "สวัสดีครับวันนี้อากาศดีมากเลยนะครับผมชื่อสมชายครับ",
        "expected": "สวัสดีครับ วันนี้อากาศดีมากเลยนะครับ ผมชื่อสมชายครับ",
        "metrics": ["punctuation_added", "no_content_loss"],
    },
]
```

### 9.4 Performance Benchmarks

```python
def benchmark_refinement_speed():
    """Measure tokens/sec for different models"""
    models = ["qwen2.5-7b-4bit", "gemma-2-9b-4bit"]
    test_text = load_test_transcript(length=10_000)  # 10K chars

    for model in models:
        processor = MLXLLMProcessor(model=model)
        start = time.time()
        refined = processor.refine_text(test_text, SYSTEM_PROMPT_TH)
        elapsed = time.time() - start

        tokens = len(refined) / 4  # Approx Thai tokens
        throughput = tokens / elapsed

        print(f"{model}: {throughput:.1f} tokens/sec")
```

---

## 10. Deployment Considerations

### 10.1 Model Download & Setup

```bash
# Download MLX-LM model (run once)
python scripts/download_llm_models.py

# Expected downloads:
# ~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-7B-Instruct-4bit/
#   ├── config.json
#   ├── model.safetensors (3.5 GB)
#   ├── tokenizer.json
#   └── weights.npz
```

### 10.2 System Requirements

**Minimum**:
- Apple Silicon Mac (M1 or later)
- 16 GB RAM
- 10 GB free storage (for models)
- macOS 12.0+

**Recommended**:
- M2 Pro or later
- 16 GB+ RAM
- 20 GB free storage
- Latest macOS

### 10.3 Configuration Files

```yaml
# config/refinement.yaml
refinement:
  enabled: true

  model:
    name: "mlx-community/Qwen2.5-7B-Instruct-4bit"
    quantization: "4bit"
    cache_dir: "~/.cache/huggingface"

  chunking:
    max_chars: 80000
    overlap_chars: 2000
    strategy: "paragraph_aware"

  processing:
    max_retries: 3
    timeout_seconds: 300
    fallback_to_raw: true

  prompts:
    language_map:
      th: "prompts/refine_thai.txt"
      en: "prompts/refine_english.txt"
```

### 10.4 Monitoring & Logging

```python
# Enhanced logging for refinement
logger.info(f"Refinement started: {num_chunks} chunks")
logger.info(f"Model: {model_name}, quantization: {quantization}")
logger.info(f"Expected time: ~{estimated_time:.1f} minutes")

for i, chunk in enumerate(chunks, 1):
    logger.info(f"Processing chunk {i}/{num_chunks} ({i/num_chunks*100:.1f}%)")
    # ... process ...
    logger.info(f"Chunk {i} complete: {elapsed:.1f}s")

logger.info(f"Refinement complete: {total_time:.1f} minutes")
logger.info(f"Throughput: {tokens_per_sec:.1f} tokens/sec")
```

### 10.5 Graceful Degradation

```python
# Fallback strategy
REFINEMENT_STRATEGY = {
    "primary": {
        "model": "qwen2.5-7b-instruct-4bit",
        "max_memory": 6_000_000_000,  # 6 GB
    },
    "fallback": {
        "model": "qwen2.5-3b-instruct-4bit",  # Smaller model
        "max_memory": 3_000_000_000,  # 3 GB
    },
    "emergency": {
        "model": None,  # Skip refinement
        "return_raw": True,
    }
}
```

---

## 11. Risk Assessment & Mitigation

### 11.1 Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **LLM hallucinates** | High | Medium | • Strict prompt engineering<br>• Validation against raw<br>• User review workflow |
| **Out of memory** | High | Low | • Use 4-bit quantization<br>• Sequential processing<br>• Fallback to smaller model |
| **Slow refinement** | Medium | Medium | • Optimize chunk sizes<br>• Profile and tune<br>• Optional feature (skip if slow) |
| **Quality regression** | High | Low | • Extensive testing<br>• A/B comparison<br>• Fallback to raw |
| **Model unavailable** | Low | Low | • Local caching<br>• Pre-download in setup<br>• Graceful fallback |

### 11.2 Quality Control

1. **Diff Generation**: Show before/after comparison
2. **Validation Rules**:
   - Length change < 10%
   - No content removal
   - Only formatting/punctuation changes
3. **User Review**: Optional manual review step
4. **Metrics Tracking**: Log quality metrics over time

---

## 12. Alternative Approaches Considered

### 12.1 Alternative 1: Rule-Based Punctuation

**Approach**: Use linguistic rules instead of LLM

**Pros**:
- Fast (no LLM inference)
- Predictable
- Low memory

**Cons**:
- Limited to punctuation only
- No context-aware corrections
- Poor quality for Thai

**Verdict**: ❌ Not recommended (too limited)

### 12.2 Alternative 2: Cloud LLM API

**Approach**: Use OpenAI GPT-4 or Claude API

**Pros**:
- Best quality
- No local resources
- Regular updates

**Cons**:
- ❌ Violates "local LLM" requirement
- Cost per request
- Privacy concerns
- Network dependency

**Verdict**: ❌ Rejected (requirement: local LLM)

### 12.3 Alternative 3: Fine-tuned Small Model

**Approach**: Fine-tune tiny model specifically for punctuation

**Pros**:
- Very fast
- Low memory
- Specialized

**Cons**:
- Requires training data
- Limited capabilities
- Maintenance overhead

**Verdict**: ⚠️ Future enhancement (Phase 5+)

---

## 13. Success Metrics

### 13.1 Performance Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Overall Speed** | ≥2x realtime | Total time / audio length |
| **Refinement Speed** | ≥20 tokens/sec | Tokens generated / time |
| **Memory Usage** | ≤12 GB peak | Activity Monitor |
| **Success Rate** | ≥99% | Successful refinements / total |

### 13.2 Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Punctuation Accuracy** | ≥95% | Manual evaluation (sample) |
| **Content Preservation** | 100% | Automated diff check |
| **Paragraph Quality** | ≥90% satisfaction | User feedback |
| **Typo Corrections** | ≥80% correct | Test set evaluation |

### 13.3 User Experience Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| **Setup Time** | ≤5 minutes | First-time setup |
| **CLI Usability** | ≥4/5 rating | User survey |
| **Error Rate** | ≤1% | Failed refinements / total |

---

## 14. Cost-Benefit Analysis

### 14.1 Development Cost

| Phase | Time | Effort |
|-------|------|--------|
| Phase 1: Core | 1 week | 40 hours |
| Phase 2: Chunking | 1 week | 40 hours |
| Phase 3: Integration | 1 week | 40 hours |
| Phase 4: Optimization | 1 week | 40 hours |
| **Total** | **4 weeks** | **160 hours** |

### 14.2 Benefits

**Quantitative**:
- ✅ 80-90% reduction in manual editing time
- ✅ Professional-quality transcripts
- ✅ Competitive feature vs paid services

**Qualitative**:
- ✅ Better user experience
- ✅ Increased trust in transcripts
- ✅ Reduces post-processing workload

### 14.3 Return on Investment

**Example**: 10-hour audio transcription workload per week

| Scenario | Time | Quality |
|----------|------|---------|
| **Without Refinement** | 10h audio → 20h manual editing | Good |
| **With Refinement** | 10h audio → 5h review/touch-up | Excellent |
| **Time Saved** | 15 hours/week | +Quality improvement |

**ROI**: 4-week development → ongoing 15h/week savings = break-even at 11 weeks

---

## 15. Recommendations Summary

### 15.1 Primary Recommendations

1. ✅ **Use MLX-LM** with Qwen2.5-7B-Instruct-4bit
   - Native Apple Silicon support
   - Best Thai language quality
   - Optimal performance/memory trade-off

2. ✅ **Post-processing architecture**
   - Transcribe fully first, then refine
   - Simpler implementation
   - Easier debugging

3. ✅ **Single-pass refinement**
   - One LLM call per chunk
   - Target: 2x realtime overall
   - Multi-pass as optional enhancement

4. ✅ **Paragraph-aware chunking**
   - 80K char chunks
   - 2K char overlap
   - Smart merging

5. ✅ **Graceful fallback**
   - Always save raw transcript
   - Skip refinement if errors
   - User-configurable

### 15.2 Implementation Roadmap

```
Week 1: Core Refinement Service
  ├── MLX-LM integration
  ├── Basic prompt templates
  └── CLI interface

Week 2: Chunking & Merging
  ├── Text chunker
  ├── Smart merger
  └── Long transcript support

Week 3: Pipeline Integration
  ├── Wizard integration
  ├── Progress tracking
  └── Error handling

Week 4: Optimization
  ├── Performance tuning
  ├── Quality evaluation
  └── Documentation
```

### 15.3 Go/No-Go Decision Criteria

**Proceed if**:
- ✅ Refinement maintains ≥2x realtime speed
- ✅ Quality improvement visible in manual tests
- ✅ Memory usage stays ≤12 GB
- ✅ 99%+ reliability

**Reconsider if**:
- ❌ Speed drops below 1.5x realtime
- ❌ Quality no better than raw
- ❌ Frequent OOM errors
- ❌ Model download issues

---

## 16. Next Steps

### Immediate Actions (Week 1)

1. **Install MLX-LM**
   ```bash
   pip install mlx-lm>=0.18.0
   ```

2. **Download Qwen2.5-7B-Instruct-4bit**
   ```python
   from mlx_lm import load
   model, tokenizer = load("mlx-community/Qwen2.5-7B-Instruct-4bit")
   ```

3. **Create Basic Prototype**
   - Simple CLI script
   - Single chunk refinement
   - Measure baseline performance

4. **Quality Testing**
   - Test with 3-5 real Thai transcripts
   - Manual evaluation
   - Document quality improvements

### Future Enhancements (Post-MVP)

1. **Streaming Refinement**
   - Refine while transcribing
   - Reduce total time

2. **Multi-pass Refinement**
   - Separate passes for punctuation, paragraphs, corrections
   - Higher quality, slower

3. **Custom Fine-tuning**
   - Fine-tune on domain-specific data
   - Improved accuracy for technical terms

4. **Model Selection UI**
   - Let users choose model (Qwen vs Typhoon vs Gemma)
   - Quality vs speed trade-off

5. **Diff Visualization**
   - HTML diff viewer
   - Track changes made by LLM

---

## Appendix A: Sample Prompts

### A.1 Thai System Prompt (Production)

```python
SYSTEM_PROMPT_TH_PRODUCTION = """คุณเป็น AI ผู้เชี่ยวชาญในการปรับปรุงข้อความที่ได้จากการถอดเสียงอัตโนมัติ (speech-to-text)

งานของคุณคือปรับปรุงข้อความให้อ่านง่ายขึ้น โดย:

1. **เพิ่มเครื่องหมายวรรคตอน**
   - จุด (.) ท้ายประโยค
   - จุลภาค (,) เพื่อแยกส่วนประโยค
   - เครื่องหมายคำถาม (?) สำหรับคำถาม
   - เครื่องหมายอัศเจรีย์ (!) เมื่อเหมาะสม

2. **แบ่งย่อหน้า**
   - แยกย่อหน้าเมื่อเปลี่ยนหัวข้อ
   - แยกย่อหน้าเมื่อเปลี่ยนผู้พูด (ถ้าเห็นได้ชัด)
   - คงย่อหน้าไว้ 3-5 ประโยคต่อย่อหน้า

3. **แก้ไขคำผิด**
   - แก้คำที่อาจจะได้ยินผิดโดยใช้บริบทโดยรอบ
   - แก้ไขเฉพาะเมื่อแน่ใจว่าผิดชัดเจน
   - ถ้าไม่แน่ใจ ให้คงคำเดิมไว้

4. **จัดรูปแบบ**
   - ใช้ช่องว่างสม่ำเสมอ
   - ตัวเลขเขียนเป็นตัวเลขอารบิค (1, 2, 3) ยกเว้นบริบทเฉพาะ
   - ใช้เครื่องหมายคำพูด "" สำหรับคำพูดตรง

**ข้อห้าม**:
- ❌ ห้ามเปลี่ยนแปลงเนื้อหา ความหมาย หรือข้อมูล
- ❌ ห้ามเพิ่มข้อมูลใหม่ที่ไม่มีในต้นฉบับ
- ❌ ห้ามสรุป ตัดทอน หรือข้ามข้อความ
- ❌ ห้ามแปลหรือเปลี่ยนภาษา

**รูปแบบการตอบ**:
- ตอบกลับเฉพาะข้อความที่ปรับปรุงแล้ว
- ไม่ต้องอธิบายหรือแสดงความคิดเห็น
- ไม่ต้องใส่หัวข้อหรือ metadata

ให้ใช้ภาษาไทยมาตรฐานที่ถูกต้อง สุภาพ และอ่านง่าย"""
```

### A.2 English System Prompt

```python
SYSTEM_PROMPT_EN_PRODUCTION = """You are an AI expert at improving automatically transcribed speech-to-text output.

Your task is to improve readability by:

1. **Adding punctuation**
   - Periods (.) at sentence ends
   - Commas (,) to separate clauses
   - Question marks (?) for questions
   - Exclamation marks (!) when appropriate

2. **Breaking into paragraphs**
   - New paragraph when topic changes
   - New paragraph when speaker changes (if detectable)
   - Keep paragraphs 3-5 sentences long

3. **Correcting errors**
   - Fix misheard words using surrounding context
   - Only correct when error is obvious
   - When uncertain, keep original text

4. **Formatting**
   - Consistent spacing
   - Capitalize proper nouns, acronyms
   - Use quotation marks for direct speech

**Restrictions**:
- ❌ Do not change content, meaning, or information
- ❌ Do not add new information not in original
- ❌ Do not summarize, shorten, or skip text
- ❌ Do not translate or change language

**Response format**:
- Return only the improved text
- No explanations or comments
- No titles or metadata

Use standard, polite, and readable language."""
```

---

## Appendix B: Code Snippets

### B.1 MLX-LM Processor Implementation

```python
"""
MLX-LM Processor for Transcript Refinement
File: app/services/llm_refinement/llm_processor.py
"""

import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class MLXLLMProcessor:
    """
    MLX-LM wrapper for transcript refinement.

    Uses Apple's MLX framework for efficient LLM inference on Apple Silicon.
    """

    def __init__(
        self,
        model_name: str = "mlx-community/Qwen2.5-7B-Instruct-4bit",
        max_tokens: int = 100_000,
        temperature: float = 0.3,
    ):
        """
        Initialize MLX-LM processor.

        Args:
            model_name: HuggingFace model name (must be MLX-compatible)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (lower = more conservative)
        """
        self.model_name = model_name
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.model = None
        self.tokenizer = None

        logger.info(f"Initializing MLX-LM: {model_name}")
        self._load_model()

    def _load_model(self):
        """Load MLX model and tokenizer."""
        try:
            from mlx_lm import load

            logger.info("Loading MLX model (this may take 30-60 seconds)...")
            self.model, self.tokenizer = load(self.model_name)
            logger.info("✓ MLX model loaded successfully")

        except ImportError:
            raise RuntimeError(
                "mlx-lm not installed. Install with: pip install mlx-lm"
            )
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def refine_text(
        self,
        text: str,
        system_prompt: str,
        max_retries: int = 3,
    ) -> str:
        """
        Refine text using LLM.

        Args:
            text: Raw transcript text to refine
            system_prompt: System instruction for LLM
            max_retries: Number of retries on failure

        Returns:
            Refined text

        Raises:
            RuntimeError: If refinement fails after retries
        """
        from mlx_lm import generate

        # Construct prompt
        prompt = self._construct_prompt(system_prompt, text)

        # Generate with retries
        for attempt in range(max_retries):
            try:
                logger.debug(f"Generating (attempt {attempt + 1}/{max_retries})...")

                response = generate(
                    model=self.model,
                    tokenizer=self.tokenizer,
                    prompt=prompt,
                    max_tokens=self.max_tokens,
                    temperature=self.temperature,
                    verbose=False,
                )

                refined = self._extract_response(response)

                # Validate output
                if self._validate_output(text, refined):
                    logger.debug(f"Generation successful ({len(refined)} chars)")
                    return refined
                else:
                    logger.warning(f"Validation failed (attempt {attempt + 1})")
                    continue

            except Exception as e:
                logger.error(f"Generation error (attempt {attempt + 1}): {e}")
                if attempt == max_retries - 1:
                    raise RuntimeError(f"Refinement failed after {max_retries} attempts") from e
                continue

        # Fallback: return original if all retries failed
        logger.warning("All retries failed, returning original text")
        return text

    def _construct_prompt(self, system_prompt: str, text: str) -> str:
        """Construct prompt for Qwen-style instruction model."""
        return f"""<|im_start|>system
{system_prompt}<|im_end|>
<|im_start|>user
ปรับปรุงข้อความที่ถอดเสียงนี้:

{text}

ข้อความที่ปรับปรุงแล้ว:<|im_end|>
<|im_start|>assistant
"""

    def _extract_response(self, response: str) -> str:
        """Extract refined text from model response."""
        # Remove any special tokens or metadata
        refined = response.strip()

        # Remove instruction markers if present
        if "<|im_start|>" in refined:
            refined = refined.split("<|im_start|>")[-1]
        if "<|im_end|>" in refined:
            refined = refined.split("<|im_end|>")[0]

        return refined.strip()

    def _validate_output(self, original: str, refined: str) -> bool:
        """
        Validate refined output.

        Checks:
        - Length change < 20%
        - Not empty
        - Contains Thai characters (for Thai text)

        Args:
            original: Original text
            refined: Refined text

        Returns:
            True if valid, False otherwise
        """
        if not refined or len(refined) < 10:
            logger.warning("Refined text too short or empty")
            return False

        # Check length change
        length_ratio = len(refined) / len(original)
        if length_ratio < 0.8 or length_ratio > 1.2:
            logger.warning(f"Length change too large: {length_ratio:.2f}x")
            return False

        # For Thai text, check if Thai characters present
        if any('\u0E00' <= c <= '\u0E7F' for c in original):
            if not any('\u0E00' <= c <= '\u0E7F' for c in refined):
                logger.warning("Thai characters missing in refined text")
                return False

        return True

    def get_model_info(self) -> Dict[str, Any]:
        """Get model information."""
        return {
            "model_name": self.model_name,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "loaded": self.model is not None,
        }
```

### B.2 Text Chunker Implementation

```python
"""
Smart Text Chunker for LLM Processing
File: app/services/llm_refinement/chunker.py
"""

import logging
import re
from typing import List, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a text chunk with metadata."""
    index: int
    text: str
    start_char: int
    end_char: int
    has_overlap_before: bool
    has_overlap_after: bool


class TextChunker:
    """
    Smart text chunker with paragraph awareness.

    Splits long text into chunks suitable for LLM processing while:
    - Respecting paragraph boundaries
    - Adding overlap for context
    - Preserving sentence integrity
    """

    def __init__(
        self,
        max_chars: int = 80_000,
        overlap_chars: int = 2_000,
        paragraph_aware: bool = True,
    ):
        """
        Initialize chunker.

        Args:
            max_chars: Maximum characters per chunk
            overlap_chars: Overlap between consecutive chunks
            paragraph_aware: Try not to split paragraphs
        """
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.paragraph_aware = paragraph_aware

        logger.info(f"Text Chunker: max={max_chars}, overlap={overlap_chars}")

    def split_text(self, text: str) -> List[TextChunk]:
        """
        Split text into chunks.

        Args:
            text: Input text

        Returns:
            List of TextChunk objects
        """
        if len(text) <= self.max_chars:
            # Single chunk
            return [TextChunk(
                index=0,
                text=text,
                start_char=0,
                end_char=len(text),
                has_overlap_before=False,
                has_overlap_after=False,
            )]

        # Split into chunks
        chunks = []
        current_pos = 0
        chunk_index = 0

        while current_pos < len(text):
            # Determine chunk end position
            chunk_end = min(current_pos + self.max_chars, len(text))

            # Adjust to paragraph boundary if enabled
            if self.paragraph_aware and chunk_end < len(text):
                chunk_end = self._find_paragraph_boundary(
                    text,
                    chunk_end,
                    search_back=min(1000, self.max_chars // 10)
                )

            # Extract chunk text
            chunk_text = text[current_pos:chunk_end]

            # Add overlap if not first chunk
            if current_pos > 0:
                overlap_start = max(0, current_pos - self.overlap_chars)
                overlap_text = text[overlap_start:current_pos]
                chunk_text = overlap_text + chunk_text

            # Create chunk
            chunk = TextChunk(
                index=chunk_index,
                text=chunk_text,
                start_char=current_pos,
                end_char=chunk_end,
                has_overlap_before=(current_pos > 0),
                has_overlap_after=(chunk_end < len(text)),
            )
            chunks.append(chunk)

            # Move to next chunk
            current_pos = chunk_end
            chunk_index += 1

        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks

    def _find_paragraph_boundary(
        self,
        text: str,
        position: int,
        search_back: int = 1000,
    ) -> int:
        """
        Find nearest paragraph boundary before position.

        Args:
            text: Full text
            position: Target position
            search_back: How far to search backwards

        Returns:
            Adjusted position at paragraph boundary
        """
        # Search window
        start = max(0, position - search_back)
        search_text = text[start:position]

        # Look for paragraph markers (double newline, or Thai paragraph)
        # Thai paragraphs often have single newline or indent
        paragraph_markers = [
            '\n\n',  # Double newline
            '\n ',   # Newline + space (indent)
            '\n\t',  # Newline + tab
        ]

        best_boundary = position
        for marker in paragraph_markers:
            idx = search_text.rfind(marker)
            if idx != -1:
                boundary = start + idx + len(marker)
                if boundary > start:
                    best_boundary = boundary
                    break

        # If no paragraph found, try sentence boundary
        if best_boundary == position:
            sentence_end = re.search(r'[.!?]\s+', search_text[::-1])
            if sentence_end:
                best_boundary = position - sentence_end.start()

        return best_boundary
```

---

## Appendix C: Performance Estimation Details

### C.1 Token Generation Speed Estimates

**MLX-LM on M2 Pro (10-core CPU, 16-core GPU, 16GB RAM)**:

| Model | Quantization | Params | Memory | Tokens/sec | Source |
|-------|--------------|--------|--------|------------|--------|
| Qwen2.5-7B | 4-bit | 7B | 3.8 GB | 25-30 | Estimated |
| Qwen2.5-7B | 8-bit | 7B | 7.2 GB | 15-20 | Estimated |
| Gemma-2-9B | 4-bit | 9B | 4.8 GB | 18-22 | Estimated |
| Llama-3.2-8B | 4-bit | 8B | 4.2 GB | 20-25 | Estimated |

**Notes**:
- Actual speeds vary based on prompt length and context
- First token latency: 0.5-1.0 seconds
- Subsequent tokens: steady throughput as listed

### C.2 End-to-End Time Breakdown

**Example**: 120-minute audio file with Medium Whisper model

```
Total Audio: 120 minutes (2 hours)

STAGE 1: Preprocessing
├── Audio loading: 10 sec
├── Noise reduction: 2 min
├── Chunking: 30 sec
└── Total: 3 min

STAGE 2: Transcription (MLX Whisper Medium, 2×8)
├── Model loading: 10 sec
├── Transcription: 28 min (4.3x realtime)
└── Total: 30 min

STAGE 3: Refinement (Qwen2.5-7B-4bit) ⭐ NEW
├── Model loading: 45 sec
├── Text chunking: 5 sec
├── LLM processing:
│   ├── Transcript length: ~150,000 chars
│   ├── Chunks: 2 (with overlap)
│   ├── Per chunk: 13 min
│   └── Total: 26 min
├── Merging: 10 sec
└── Total: 27 min

STAGE 4: Output Generation
├── File writing: 5 sec
├── SRT generation: 10 sec
└── Total: 15 sec

═══════════════════════════════════════════
GRAND TOTAL: 60 minutes
Overall Speed: 2.0x realtime
═══════════════════════════════════════════

Breakdown:
- Preprocessing: 3 min (5%)
- Transcription: 30 min (50%)
- Refinement: 27 min (45%)
- Output: 0.25 min (<1%)
```

---

## Appendix D: Model Download Instructions

### D.1 Automatic Download Script

```python
"""
Download LLM models for refinement
File: scripts/download_llm_models.py
"""

import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_models():
    """Download recommended LLM models."""
    from mlx_lm import load

    models = [
        {
            "name": "mlx-community/Qwen2.5-7B-Instruct-4bit",
            "description": "Primary model (Thai + Multilingual)",
            "size": "3.8 GB",
        },
        # Optional: Add backup models
        # {
        #     "name": "mlx-community/Gemma-2-9b-it-4bit",
        #     "description": "Alternative model",
        #     "size": "4.8 GB",
        # },
    ]

    for model_info in models:
        logger.info(f"=" * 60)
        logger.info(f"Downloading: {model_info['name']}")
        logger.info(f"Description: {model_info['description']}")
        logger.info(f"Size: {model_info['size']}")
        logger.info(f"=" * 60)

        try:
            model, tokenizer = load(model_info["name"])
            logger.info(f"✓ Successfully downloaded: {model_info['name']}")

            # Cleanup to free memory
            del model, tokenizer

        except Exception as e:
            logger.error(f"✗ Failed to download {model_info['name']}: {e}")
            continue

    logger.info("")
    logger.info("=" * 60)
    logger.info("✓ Model download complete!")
    logger.info("=" * 60)


if __name__ == "__main__":
    download_models()
```

### D.2 Manual Download

```bash
# Option 1: Download via Python
python -c "from mlx_lm import load; load('mlx-community/Qwen2.5-7B-Instruct-4bit')"

# Option 2: Download via CLI
huggingface-cli download mlx-community/Qwen2.5-7B-Instruct-4bit

# Models are cached in:
# ~/.cache/huggingface/hub/
```

---

**End of Technical Analysis Document**

---

**Document Control**:
- **Version**: 1.0
- **Date**: 2025-12-08
- **Status**: Draft for Review
- **Next Review**: After Phase 1 prototype
- **Approver**: Development Planner Agent

