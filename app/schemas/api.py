from pydantic import BaseModel


class GenerateResponse(BaseModel):
    contract_code: str
    test_code: str
    contract_filename: str
    test_filename: str
    class_name: str
    file_type: str
    record_count: int


class ErrorResponse(BaseModel):
    error: str
