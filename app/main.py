from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers.contracts import router as contracts_router

app = FastAPI(
    title="Data Contract Generator",
    description="Auto-detect file types (JSON/XML/CSV) and generate Pydantic v2 data contracts with tests.",
    version="1.0.0",
)

app.include_router(contracts_router)

output_dir = Path('output')
output_dir.mkdir(parents=True, exist_ok=True)
