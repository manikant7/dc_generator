# Data Contract Generator

A FastAPI web application that auto-detects JSON, XML, and CSV files, then generates Pydantic v2 data contracts and pytest test files.

## Features

- **Auto-detection** — Identifies file type by extension and content (JSON → XML → CSV fallback)
- **Type inference** — Detects `int`, `float`, `bool`, `str`, `date`, `datetime`, enums, nested models, `Optional`, and `List` types
- **Pydantic v2 contracts** — Generates `BaseModel` classes with `Field` descriptions and example values
- **pytest generation** — Creates test files that validate sample data against the generated contract
- **Dual input** — Accept file paths on the server or upload files through the browser
- **Web UI** — Clean one-page interface with file path/upload tabs, code display, copy, and download

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

1. Enter a server file path or upload a file (JSON, XML, or CSV)
2. Click **Generate**
3. View the generated contract and test code
4. Copy to clipboard or download `.py` files

### API

#### `GET /` — Web UI

#### `POST /generate` — Generate contract + tests

```bash
# File path
curl -X POST http://localhost:8000/generate \
  -d "file_path=/path/to/data.json"

# File upload
curl -X POST http://localhost:8000/generate \
  -F "file=@data.json"
```

Response JSON includes `contract_code`, `test_code`, `contract_filename`, `test_filename`, `class_name`, `file_type`, `record_count`.

#### `GET /download/{filename}` — Download generated files

```bash
curl -O http://localhost:8000/download/user_contract.py
```

### Running the generated tests

Generated test files are saved to the `output/` directory along with sample data:

```bash
pytest output/user_test.py -v
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
Input → Detector → Parser → Inferrer → Contract Generator → .py file
                                      → Test Generator → .py file + sample.json
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
