from pydantic import BaseModel


class GenerateResult(BaseModel):
    contract_code: str
    test_code: str
    contract_filename: str
    test_filename: str
    class_name: str
    file_type: str
    record_count: int
    source_label: str


class GenerateBatchResponse(BaseModel):
    results: list[GenerateResult]
    errors: list[str]


class ErrorResponse(BaseModel):
    detail: str
