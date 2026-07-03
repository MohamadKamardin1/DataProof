"""Pydantic models for charting endpoints."""

from pydantic import BaseModel


class ChartSpec(BaseModel):
    """A single chart specification suitable for Plotly.js frontend rendering."""
    figure_json: dict
    title: str
    chart_type: str  # "scatter" | "bar" | "line" | "ternary"


class ChartsResponse(BaseModel):
    pack_id: str
    pack_name: str
    charts: list[ChartSpec]
