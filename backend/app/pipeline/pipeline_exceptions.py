"""Pipeline-specific errors (no bank names in messages — field keys only)."""


class BankConfigMappingError(ValueError):
    """Scout blueprint missing a column or layout mapping required for extraction."""

    def __init__(self, message: str, field: str = "") -> None:
        super().__init__(message)
        self.field = field
