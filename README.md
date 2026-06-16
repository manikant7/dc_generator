# Data Contract Generator

A FastAPI web application that auto-detects JSON, XML, and CSV data, then generates Pydantic v2 data contracts and pytest test files.

## Features

- **Auto-detection** — Identifies file type by extension and content (JSON → XML → CSV fallback)
- **Type inference** — Detects `int`, `float`, `bool`, `str`, `date`, `datetime`, enums, nested models, `Optional`, and `List` types
- **Pydantic v2 contracts** — Generates `BaseModel` classes with `Field` descriptions
- **pytest generation** — Creates test files that validate sample data against the generated contract
- **Multiple input methods** — File paths, file upload (single or multiple), or paste raw data
- **Batch processing** — Process multiple files at once via paths or upload
- **Max records** — Limit the number of sample records used for contract generation
- **Partitioned output** — Each model gets its own directory with contract, tests, and sample data
- **Resizable code panels** — Vertically resizable with word wrap and line number toggles
- **41 unit tests** — Comprehensive test coverage for all service modules

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 in your browser.

## Usage

### Web UI

Three input tabs:

| Tab | Description |
|---|---|
| **File Paths** | One or more server file paths (one per line). Optional max records. |
| **Upload** | Select one or more files via the browser. Optional max records. |
| **Paste Data** | Paste JSON/XML/CSV content directly, enter a model name, optionally pick data type or use auto-detect. |

After generation, each result card shows:
- Contract and test code in resizable panels
- **Wrap** toggle — enable word wrap for long lines
- **Lines** toggle — show/hide line numbers
- **Copy** button — copy code to clipboard
- **Download** link — download the `.py` file

### API

#### `POST /generate` — Generate contract + tests

```bash
# File path(s)
curl -X POST http://localhost:8000/generate \
  -d "file_paths=/path/to/users.json" \
  -d "max_records=100"

# Multiple file paths (newline separated)
curl -X POST http://localhost:8000/generate \
  -d "file_paths=/path/to/users.json%0A/path/to/products.csv"

# File upload (single or multiple)
curl -X POST http://localhost:8000/generate \
  -F "files=@users.json" \
  -F "files=@products.csv"

# Paste raw data
curl -X POST http://localhost:8000/generate \
  -F "raw_data=[{\"id\":1,\"name\":\"Alice\"}]" \
  -F "model_name=User" \
  -F "data_type=json"
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `file_paths` | string | One or more file paths, newline-separated |
| `files` | file(s) | Uploaded file(s) (use multiple `-F` flags) |
| `raw_data` | string | Raw data content (JSON/XML/CSV) |
| `model_name` | string | Required with `raw_data` |
| `data_type` | string | `json`, `xml`, `csv`, or empty for auto-detect |
| `max_records` | int | Limit sample records used for inference |

**Response:** Returns a JSON object with `results` (array) and `errors` (array). Each result contains `contract_code`, `test_code`, `contract_filename`, `test_filename`, `class_name`, `file_type`, `record_count`, `source_label`.

#### `GET /download/{model_name}/{filename}` — Download generated files

```bash
curl -O http://localhost:8000/download/user/user_contract.py
```

Download links are also provided in the web UI.

### Running the generated tests

Generated files are saved to partitioned directories under `output/`:

```bash
pytest output/user/ -v
```

### Running the project's own tests

```bash
python -m pytest tests/ -v
```

## Architecture

```
app/
├── main.py                  # FastAPI app
├── routers/
│   └── contracts.py         # API endpoints
├── services/
│   ├── detector.py          # File type detection
│   ├── parser.py            # JSON/XML/CSV parsing
│   ├── inferrer.py          # Type inference engine
│   ├── contract_generator.py # Pydantic model generation
│   └── test_generator.py    # pytest generation
├── schemas/
│   └── api.py               # Response models
└── templates/
    └── index.html           # Web UI
```

### Pipeline

```
Input → Detector → Parser → Inferrer → Contract Generator → output/{model}/_contract.py
                                       → Test Generator  → output/{model}/_test.py + _sample.json
```

### Output structure

```
output/
├── user/
│   ├── user_contract.py
│   ├── user_test.py
│   └── user_sample.json
├── product/
│   ├── product_contract.py
│   ├── product_test.py
│   └── product_sample.json
└── uploads/             # Temporary uploaded files
```

## Type Inference

| Source | Detected types |
|---|---|
| `"123"` / `123` | `int` |
| `"12.5"` / `12.5` | `float` |
| `"true"` / `true` | `bool` |
| `"2024-01-15"` | `date` |
| `"2024-01-15T10:30:00"` | `datetime` |
| Repeating string values (2–5 unique, ≥50% repetition) | `Enum` |
| Nested objects | Separate `BaseModel` classes |
| Arrays of objects | `List[NestedModel]` |
| Empty/missing values | `Optional[T]` |

## Requirements

- Python ≥ 3.10
- fastapi
- uvicorn
- Jinja2
- pydantic ≥ 2.0
- python-multipart
