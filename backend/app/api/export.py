"""Data export API (Decision #29):

  GET  /api/v1/export/xlsx            download a single workbook (one tab per entity)
  POST /api/v1/export/to-folder       write one .xlsx per entity to a server-side folder
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import Principal, get_current_principal, require_write
from app.services import export_data

router = APIRouter(prefix="/api/v1/export", tags=["export"])

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/xlsx")
def export_xlsx(
    db: Session = Depends(get_db),
    _: Principal = Depends(get_current_principal),
):
    """Full export as a single multi-tab XLSX workbook (download)."""
    content = export_data.build_workbook(db)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"pfm_export_{stamp}.xlsx"
    return Response(
        content=content,
        media_type=XLSX_MIME,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class FolderExportIn(BaseModel):
    folder: str


@router.post("/to-folder")
def export_to_folder(
    payload: FolderExportIn,
    db: Session = Depends(get_db),
    _: Principal = Depends(require_write),
):
    """Write one .xlsx per entity into a server-accessible folder."""
    try:
        paths = export_data.write_separate_files(db, payload.folder)
    except OSError as exc:
        raise HTTPException(status_code=400, detail=f"Cannot write to folder: {exc}") from exc
    return {"folder": payload.folder, "files": paths, "count": len(paths)}


ALL_ROUTERS = [router]