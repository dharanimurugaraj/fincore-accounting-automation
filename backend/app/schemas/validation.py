from pydantic import BaseModel
from typing import Literal


class ValidationCheck(BaseModel):
    name: str
    computed: float
    bank_stated: float
    difference: float
    status: Literal["PASS", "WARN", "FAIL"]
    tolerance: float = 1.0


class ValidationResult(BaseModel):
    passed: bool
    blocked: bool
    checks: list[ValidationCheck]
    warnings: list[ValidationCheck]


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"
    service: str = "fincore-api"
