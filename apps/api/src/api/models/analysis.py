from typing import Literal

from pydantic import BaseModel, Field


class ProxyDef(BaseModel):
    id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    formula: str
    unit: str | None = None
    description: str | None = None


class ChartRecommendation(BaseModel):
    type: Literal["line", "bar", "scatter"]
    title: str
    x_axis: str
    y_axis: str


class AnalysisPack(BaseModel):
    id: str = Field(..., pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    description: str | None = None
    required_columns: list[str] = Field(min_length=1)
    proxies: list[ProxyDef] = Field(min_length=1)
    interpretation_prompt: str | None = None
    chart_recommendations: list[ChartRecommendation] = []


class PackSummary(BaseModel):
    id: str
    name: str
    description: str | None = None
    required_columns: list[str]


class AnalysisRequest(BaseModel):
    pack: str = Field(..., min_length=1)


class ProxyResult(BaseModel):
    proxy_id: str
    label: str
    sample_id: str
    value: float | None
    unit: str | None = None


class AnalysisResponse(BaseModel):
    dataset_id: int
    pack: str
    version: int
    results: list[ProxyResult]
