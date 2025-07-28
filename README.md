# Challenge 1a: PDF Heading Extraction and Structuring

## 🧠 Objective

The goal of Challenge 1a is to automatically extract a structured outline of **section headings** from arbitrary PDFs. This involves identifying text spans likely to be section titles and organizing them into a hierarchy (H1, H2, H3). The system is designed to work **on-device**, using only structural PDF features—no ML models, annotations, or metadata.

---

## 📦 Solution Overview

The system runs inside a **Docker container** and processes every `.pdf` file from `/app/input`, generating a corresponding `.json` file in `/app/output` with the detected outline.

Each JSON file contains:

- `title`: The likely document title (first H1)
- `outline`: A list of sections with their level (H1, H2, H3), text, and page number

---

## 🔍 Key Steps

### 1. **Text Span Extraction**
Using **PyMuPDF (`fitz`)**, we extract raw text spans from each page of the PDF. For each span, we record:
- Text content
- Font size
- Bold status
- Position (`x`, `y`)
- Width
- Page number

These are stored as `TextSpan` namedtuples.

---

### 2. **Font Size Tiers**
We rank unique font sizes in descending order and assign them semantic roles:
- Largest → `title`
- Next largest → `H1`
- Next → `H2`
- Next → `H3`

---

### 3. **Inter-word Gap Estimation**
For each font size, we calculate an average spacing between words. This is later used to intelligently reconstruct multi-word headings that may be broken into separate spans.

---

### 4. **Line Reconstruction**
We group spans by `(page_number, y-position)` to approximate lines. From any center span, we reconstruct surrounding spans left/right on the same line, using the estimated inter-word gap.

This ensures headings like **“Chapter 3: Results and Discussion”** are reconstructed fully even if rendered as separate spans.

---

### 5. **Heading Validation**
A span is considered a heading only if:
- The reconstructed line has ≤ 9 words
- It contains at least one word with ≥2 letters
- It’s not a pure number or Roman numeral
- For single-word lines: passes through a lexical classifier

---

### 6. **Lexical Filtering**
We use two wordlists:
- `UNLIKELY_HEADING_WORDS`: Common verbs, prepositions, and function words
- `LIKELY_HEADING_WORDS`: Domain-specific or structural terms (e.g. "Introduction", "Results", "Appendix")

These help filter out common false positives and prioritize real headings, especially when dealing with single words.

---

### 7. **Scoring and Classification**
Each candidate heading gets a **composite score** based on:
- Font size tier (`font_score`)
- Vertical and horizontal position (`position_score`)
- Bold or ALLCAPS style (`style_score`)

Score thresholds classify it into:
- `H1`: ≥ 7
- `H2`: ≥ 5
- `H3`: ≥ 3.5

---

### 8. **Deduplication**
We normalize each heading’s text (remove punctuation, lowercase, etc.) and discard duplicates across pages to avoid repeated headers.

---

### 9. **Output Generation**
Each PDF yields a JSON with:
```json
{
  "title": "Introduction",
  "outline": [
    {"level": "H1", "text": "Introduction", "page": 1},
    {"level": "H2", "text": "Background and Motivation", "page": 2},
    ...
  ]
}

---

### 10. **🏃 How to Run**

```bash
docker build -t heading-extractor .

docker run --rm \
  -v "$PWD/pdfs:/app/input" \
  -v "$PWD/output:/app/output" \
  --network none heading-extractor

### 11. Tech Stack 
- Python 3
- PyMuPDF (fitz) for PDF parsing
- Docker for containerized execution
- Pure heuristic approach (no ML dependencies)