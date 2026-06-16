import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.schemas.api import GenerateResult, GenerateBatchResponse
from app.services.detector import detect_file_type, detect_type_from_content
from app.services.parser import parse_file, parse_string
from app.services.inferrer import infer_schema
from app.services.contract_generator import generate_contract
from app.services.test_generator import generate_tests

router = APIRouter()
templates = Jinja2Templates(directory='app/templates')

OUTPUT_DIR = Path('output')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR = OUTPUT_DIR / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@router.post("/generate", response_model=GenerateBatchResponse)
async def generate(
    file_paths: str = Form(None),
    files: list[UploadFile] = File(None),
    raw_data: str = Form(None),
    model_name: str = Form(None),
    data_type: str = Form(None),
    max_records: int = Form(None),
):
    inputs = []
    errors = []

    if file_paths:
        for fp in file_paths.strip().split('\n'):
            fp = fp.strip()
            if fp:
                inputs.append(('path', fp, None))

    if files:
        for f in files:
            if f.filename:
                inputs.append(('upload', f, None))

    if raw_data:
        if not model_name or not model_name.strip():
            errors.append("model_name is required when pasting raw data")
        else:
            inputs.append(('raw', raw_data.strip(), model_name.strip()))

    if not inputs:
        if errors:
            return GenerateBatchResponse(results=[], errors=errors)
        raise HTTPException(status_code=400, detail="No input provided. Provide file_paths, files, or raw_data with model_name.")

    results = []
    for kind, data, explicit_name in inputs:
        try:
            if kind == 'path':
                result = _process_file_path(data, max_records)
            elif kind == 'upload':
                result = _process_upload(data, max_records)
            elif kind == 'raw':
                result = _process_raw(data, explicit_name, data_type, max_records)
            results.append(result)
        except HTTPException:
            raise
        except Exception as e:
            label = data if isinstance(data, str) else getattr(data, 'filename', 'unknown')
            errors.append(f"{label}: {str(e)}")

    return GenerateBatchResponse(results=results, errors=errors)


@router.get("/download/{model_name}/{filename:path}")
async def download(model_name: str, filename: str):
    file_path = OUTPUT_DIR / model_name / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {model_name}/{filename}")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="text/plain",
    )


def _process_file_path(file_path: str, max_records: int | None) -> GenerateResult:
    path = Path(file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    if not path.is_file():
        raise HTTPException(status_code=400, detail=f"Not a file: {file_path}")

    resolved = str(path.resolve())
    file_type = detect_file_type(resolved)
    records = parse_file(resolved, file_type)
    class_name = _derive_class_name(file_path)
    return _build_result(records, class_name, path.name, file_type, max_records)


def _process_upload(file: UploadFile, max_records: int | None) -> GenerateResult:
    content = file.file.read()
    safe_name = f"{uuid.uuid4().hex}_{file.filename}"
    upload_path = UPLOAD_DIR / safe_name
    upload_path.write_bytes(content)

    resolved = str(upload_path.resolve())
    file_type = detect_file_type(resolved)
    records = parse_file(resolved, file_type)
    class_name = _derive_class_name(file.filename)
    return _build_result(records, class_name, file.filename, file_type, max_records)


def _process_raw(data: str, model_name: str, data_type: str | None, max_records: int | None) -> GenerateResult:
    if not data.strip():
        raise ValueError("Raw data is empty")

    if data_type and data_type.strip():
        file_type = data_type.strip().lower()
        if file_type not in ('json', 'xml', 'csv'):
            raise ValueError(f"Unsupported data type: {file_type}. Use json, xml, or csv.")
    else:
        file_type = detect_type_from_content(data)

    records = parse_string(data, file_type)
    class_name = model_name
    return _build_result(records, class_name, f"pasted_{model_name.lower()}", file_type, max_records)


def _build_result(
    records: list[dict],
    class_name: str,
    source_label: str,
    file_type: str,
    max_records: int | None,
) -> GenerateResult:
    if not records:
        raise ValueError("No records found in data")

    sample = records[:max_records] if max_records else records

    fields = infer_schema(sample, class_name)

    model_dir = OUTPUT_DIR / class_name.lower()
    model_dir.mkdir(parents=True, exist_ok=True)

    contract_filename = f"{class_name.lower()}_contract.py"
    test_filename = f"{class_name.lower()}_test.py"

    contract_code = generate_contract(
        fields=fields,
        class_name=class_name,
        source=source_label,
        output_path=model_dir / contract_filename,
    )

    test_code = generate_tests(
        records=sample,
        fields=fields,
        class_name=class_name,
        source_path=source_label,
        file_type=file_type,
        output_dir=model_dir,
    )

    return GenerateResult(
        contract_code=contract_code,
        test_code=test_code,
        contract_filename=contract_filename,
        test_filename=test_filename,
        class_name=class_name,
        file_type=file_type,
        record_count=len(records),
        source_label=source_label,
    )


def _derive_class_name(file_path: str) -> str:
    stem = Path(file_path).stem
    stem = stem.lower()
    if stem.endswith('s') and not stem.endswith('ss'):
        stem = stem[:-1]
    parts = re.split(r'[-_\s]+', stem)
    result = ''.join(p.capitalize() for p in parts if p)
    if not result or result[0].isdigit():
        result = 'DataRecord'
    return result
