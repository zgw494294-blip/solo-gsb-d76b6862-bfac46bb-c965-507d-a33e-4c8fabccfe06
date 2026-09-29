"""共炉保温编排台 —— FastAPI 后端。"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .solver import MAX_TEMP, Material, solve

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"

app = FastAPI(title="共炉保温编排台", version="1.0.0")


class MaterialIn(BaseModel):
    name: str = Field(default="", max_length=20)
    hold_low: int = Field(alias="holdLow", ge=40, le=180)
    hold_high: int = Field(alias="holdHigh", ge=40, le=180)
    duration: int
    tolerance: int

    @field_validator("name")
    @classmethod
    def _clean_name(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("hold_low", "hold_high", "tolerance")
    @classmethod
    def _tens(cls, v: int) -> int:
        if v % 10 != 0:
            raise ValueError("温度必须是 10 的整数倍。")
        return v

    @field_validator("duration")
    @classmethod
    def _duration(cls, v: int) -> int:
        if v not in (5, 10, 15):
            raise ValueError("连续保温时长必须为 5、10 或 15 分钟。")
        return v

    model_config = {"populate_by_name": True}


class ScheduleIn(BaseModel):
    materials: list[MaterialIn] = Field(min_length=2, max_length=3)


@app.post("/api/schedule")
def schedule(payload: ScheduleIn):
    materials: list[Material] = []
    for i, item in enumerate(payload.materials):
        if item.hold_low > item.hold_high:
            raise HTTPException(
                status_code=422,
                detail=f"第 {i + 1} 种材料的保温下限不得高于保温上限。",
            )
        if item.tolerance < item.hold_high or item.tolerance > MAX_TEMP:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"材料「{item.name or i + 1}」的耐受上限必须不低于保温上限"
                    f"（{item.hold_high}°C）且至多 {MAX_TEMP}°C。"
                ),
            )
        materials.append(
            Material(
                name=item.name or f"材料{i + 1}",
                hold_low=item.hold_low,
                hold_high=item.hold_high,
                duration=item.duration,
                tolerance=item.tolerance,
            )
        )

    try:
        return solve(materials)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/healthz")
def healthz():
    return {"ok": True}


# 静态页面（/）
@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
