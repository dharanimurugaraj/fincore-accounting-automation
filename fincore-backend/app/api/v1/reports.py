"""
GET /reports, POST /reports/{id}/approve
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def list_reports():
    """List generated reports. Placeholder — will read from PipelineRun table."""
    return {"reports": [], "total": 0}


@router.post("/{report_id}/approve")
async def approve_report(report_id: str):
    """Approve a specific report. Placeholder."""
    return {"report_id": report_id, "status": "approved"}
