import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates

from app.schemas.api import GenerateResponse, ErrorResponse
from app.services.detector import detect_file_type
from app.services.parser import parse_file
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


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    file_path: str = Form(None),
    file: UploadFile = File(None),
):
    if file_path and file:
        raise HTTPException(status_code=400, detail="Provide either file_path or file, not both")
    if not file_path and not file:
        raise HTTPException(status_code=400, detail="Provide either a file path or upload a file")

    resolved_path = None
    original_filename = None

    if file:
        content = await file.read()
        original_filename = file.filename
        safe_name = f"{uuid.uuid4().hex}_{original_filename}"
        upload_path = UPLOAD_DIR / safe_name
        upload_path.write_bytes(content)
        resolved_path = str(upload_path.resolve())
    else:
        path = Path(file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        if not path.is_file():
            raise HTTPException(status_code=400, detail=f"Not a file: {file_path}")
        resolved_path = str(path.resolve())

    try:
        file_type = detect_file_type(resolved_path)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        records = parse_file(resolved_path, file_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not records:
        raise HTTPException(status_code=400, detail="No records found in file")

    class_name = _derive_class_name(original_filename or resolved_path)

    fields = infer_schema(records, class_name)

    base_name = class_name.lower()
    contract_filename = f"{base_name}_contract.py"
    test_filename = f"{base_name}_test.py"

    contract_path = OUTPUT_DIR / contract_filename
    test_path = OUTPUT_DIR / test_filename

    contract_code = generate_contract(
        fields=fields,
        class_name=class_name,
        source=str(resolved_path),
        output_path=contract_path,
    )

    test_code = generate_tests(
        records=records,
        fields=fields,
        class_name=class_name,
        source_path=str(resolved_path),
        file_type=file_type,
        output_dir=OUTPUT_DIR,
    )

    return GenerateResponse(
        contract_code=contract_code,
        test_code=test_code,
        contract_filename=contract_filename,
        test_filename=test_filename,
        class_name=class_name,
        file_type=file_type,
        record_count=len(records),
    )


@router.get("/download/{filename:path}")
async def download(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {filename}")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="text/plain",
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
