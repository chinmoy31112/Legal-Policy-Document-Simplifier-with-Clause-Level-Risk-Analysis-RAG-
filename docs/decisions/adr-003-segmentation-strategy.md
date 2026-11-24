# ADR 003: Legal Clause Segmentation Strategy (Structural Heuristics vs. Token Chunking vs. LLM)

## Status
Accepted

## Context
Legal agreements (Terms of Service, NDAs, Employment Contracts, Leases) are authored in strict hierarchical structures: sections, articles, numbered paragraphs, subclauses, bullet points, and definitions. Accurate clause segmentation is critical because downstream risk analysis, vector retrieval, and PDF highlight overlays rely on precise clause boundaries and bounding boxes.

We evaluated three segmentation approaches:
1. **Multi-Pass Structural Heuristics (PyMuPDF Layout + Regex Grammar)**: Detects font size/weight variations, numbered legal patterns (e.g., `1.1`, `(a)`, `Section 4`), and indentation hierarchies.
2. **Fixed Token / Sliding Window Chunking** (e.g., LangChain RecursiveCharacterTextSplitter at 512 tokens): Slices documents based on character and token count.
3. **LLM-Based Segmentation** (Passing full raw document text to Gemini to return segmented clauses).

## Trade-offs in Three Lines
1. **Structural Heuristics** extract legally meaningful clause units while preserving exact PyMuPDF bounding-box coordinates with zero latency and zero API cost.
2. **Token Chunking** is uniform and fast, but regularly cuts clauses mid-sentence, severs operative covenants from definitions, and completely corrupts PDF bounding-box mapping.
3. **LLM-Based Segmentation** captures subtle semantic transitions but is economically unviable for 50-page contracts, introduces latency bottlenecks, and cannot return precise PDF page bounding-box geometries.

## Decision
We select **Multi-Pass Structural Heuristics** implemented as pure, deterministic functions without network or database dependencies:
- **Pass 1 (Block & Style Extraction):** PyMuPDF extracts text spans with exact `(x0, y0, x1, y1)` bounding boxes, font names, font sizes, and bold/italic flags per page.
- **Pass 2 (Hierarchy & Heading Detection):** Detects major headings (larger fonts, uppercase, bold) and section markers (`ARTICLE`, `SECTION`, `CLAUSE`).
- **Pass 3 (Numbering Grammar & Subclauses):** Recognizes hierarchical numbering (`1.`, `1.1`, `(a)`, `(i)`) and attaches subordinate subclauses to their parent clause.
- **Pass 4 (Fallback Normalization):** For unformatted or continuous text blocks, segments by double-newline paragraph breaks. Every span is assigned a deterministic SHA-256 text hash.

## Consequences
- Boundary F1 target of ≥ 0.85 achievable across standardized legal contracts.
- 100% deterministic, offline execution with sub-second processing per document.
- Retains exact coordinate tuples `[page, x0, y0, x1, y1]` for visual PDF highlighting in the frontend PDF.js viewer.
