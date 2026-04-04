"""
Custom exception classes for FinCore.
"""


class FinCoreError(Exception):
    """Base exception for all FinCore errors."""
    pass


class PipelineError(FinCoreError):
    """Raised when the pipeline encounters a fatal error."""
    pass


class OCRExtractionError(FinCoreError):
    """Raised when OCR extraction fails."""
    pass


class ValidationError(FinCoreError):
    """Raised when computed values don't match bank-stated figures."""
    pass


class StorageError(FinCoreError):
    """Raised when file upload/download fails."""
    pass


class ClassificationError(FinCoreError):
    """Raised when PDF classification fails to identify the document."""
    pass
