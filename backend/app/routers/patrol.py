"""巡查任务接口：维护巡查单，覆盖派发巡查、提交结果、作废巡查等动作。"""
from __future__ import annotations

import csv
import io
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Query, Response

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.patrol import PatrolService

router = APIRouter(prefix="/api/patrol", tags=["巡查任务"])

service = PatrolService()

LIST_FIELDS = ["巡查单号", "巡查路线", "巡查人员", "巡查日期", "巡查里程", "发现问题数", "巡查时长", "巡查状态"]
STATUSES = ["待派发", "巡查中", "已提交", "已作废"]
EXPORT_SIZE = 10000
EXPORT_FILENAME = "巡查任务清单.csv"


@router.get("", response_model=PageResult[dict])
def list_entries(
    keyword: str | None = Query(default=None, description="按巡查单号检索"),
    route: str | None = Query(default=None, description="按巡查路线检索"),
    person: str | None = Query(default=None, description="按巡查人员检索"),
    status: str | None = Query(default=None, description="待派发、巡查中、已提交、已作废"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按巡查单号、路线、人员与状态过滤巡查任务列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(keyword=keyword, route=route, person=person, status=status, page=page, size=size)
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries(
    keyword: str | None = Query(default=None, description="按巡查单号检索"),
    route: str | None = Query(default=None, description="按巡查路线检索"),
    person: str | None = Query(default=None, description="按巡查人员检索"),
    status: str | None = Query(default=None, description="待派发、巡查中、已提交、已作废"),
) -> Response:
    """导出巡查任务清单：取数口径与列表完全一致；没有可导出的记录时给出说明而不是空文件。"""
    items, _ = service.list_entries(keyword=keyword, route=route, person=person, status=status, page=1, size=EXPORT_SIZE)
    if not items:
        raise HTTPException(status_code=404, detail="当前筛选条件下没有可导出的巡查记录，请调整筛选条件后再试")
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(LIST_FIELDS)
    for row in items:
        writer.writerow(["" if row.get(field) is None else str(row.get(field)) for field in LIST_FIELDS])
    content = buffer.getvalue().encode("utf-8-sig")
    headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(EXPORT_FILENAME)}"}
    return Response(content=content, media_type="text/csv; charset=utf-8", headers=headers)


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条巡查单明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"巡查单 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条巡查单，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="巡查单已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条巡查单执行派发巡查、提交结果、作废巡查；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
