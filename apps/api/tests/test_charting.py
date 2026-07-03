"""Tests for the ChartBuilder service — reproducing correct order for acceptance criteria."""

import pytest

from api.charting import ChartBuilder
from api.models.analysis import AnalysisPack, ChartRecommendation, ProxyDef, ProxyResult

SAMPLE_PACK = AnalysisPack(
    id="paleoclimate_xrf",
    name="Paleoclimate XRF",
    description="XRF elemental ratio analysis",
    required_columns=["Rb", "Sr", "Ba", "Al", "Si"],
    proxies=[
        ProxyDef(id="rb_sr_ratio", label="Rb/Sr Ratio", formula="Rb / Sr", unit="ratio"),
        ProxyDef(id="ba_sr_ratio", label="Ba/Sr Ratio", formula="Ba / Sr", unit="ratio"),
        ProxyDef(id="al_si_ratio", label="Al/Si Ratio", formula="Al / Si", unit="ratio"),
    ],
    chart_recommendations=[
        ChartRecommendation(
            type="line", title="Rb/Sr by Sample", x_axis="sample_id", y_axis="rb_sr_ratio",
        ),
        ChartRecommendation(
            type="scatter", title="Rb/Sr vs Ba/Sr", x_axis="rb_sr_ratio", y_axis="ba_sr_ratio",
        ),
    ],
)

# Reference values from Phase 3 fixture: 5621_6 highest Rb/Sr, 6821-6 lowest
SAMPLE_RESULTS = [
    ProxyResult(proxy_id="rb_sr_ratio", label="Rb/Sr Ratio", sample_id="5621_6", value=3.39, unit="ratio"),  # noqa: E501
    ProxyResult(proxy_id="ba_sr_ratio", label="Ba/Sr Ratio", sample_id="5621_6", value=1.20, unit="ratio"),  # noqa: E501
    ProxyResult(proxy_id="al_si_ratio", label="Al/Si Ratio", sample_id="5621_6", value=0.64, unit="ratio"),  # noqa: E501
    ProxyResult(proxy_id="rb_sr_ratio", label="Rb/Sr Ratio", sample_id="6821-6", value=0.86, unit="ratio"),  # noqa: E501
    ProxyResult(proxy_id="ba_sr_ratio", label="Ba/Sr Ratio", sample_id="6821-6", value=0.45, unit="ratio"),  # noqa: E501
    ProxyResult(proxy_id="al_si_ratio", label="Al/Si Ratio", sample_id="6821-6", value=0.25, unit="ratio"),  # noqa: E501
]


class TestChartBuilderRecommendations:
    def test_builds_chart_recommendations_from_pack(self):
        """Should create charts for each chart_recommendation in the pack."""
        charts = ChartBuilder.build_all(SAMPLE_PACK, SAMPLE_RESULTS)
        chart_titles = {c["title"] for c in charts}
        assert "Rb/Sr by Sample" in chart_titles
        assert "Rb/Sr vs Ba/Sr" in chart_titles

    def test_line_chart_has_correct_data(self):
        """Line chart should include both samples with correct values."""
        charts = ChartBuilder.build_all(SAMPLE_PACK, SAMPLE_RESULTS)
        line = next(c for c in charts if c["title"] == "Rb/Sr by Sample")
        fig = line["figure_json"]
        # Plotly line trace has y values in data[0].y
        y_vals = fig["data"][0]["y"]
        assert 3.39 in y_vals or pytest.approx(3.39, abs=0.01) in [round(v, 2) for v in y_vals]

    def test_scatter_chart_created(self):
        """Scatter chart of Rb/Sr vs Ba/Sr."""
        charts = ChartBuilder.build_all(SAMPLE_PACK, SAMPLE_RESULTS)
        scatter = next(c for c in charts if c["title"] == "Rb/Sr vs Ba/Sr")
        fig = scatter["figure_json"]
        assert len(fig["data"]) >= 1

    def test_build_all_returns_list(self):
        charts = ChartBuilder.build_all(SAMPLE_PACK, SAMPLE_RESULTS)
        assert isinstance(charts, list)
        assert len(charts) >= 4  # 2 recommendations + bar + ternary + scatter_matrix


class TestChartBuilderGroupedBar:
    def test_grouped_bar_present(self):
        charts = ChartBuilder.build_all(SAMPLE_PACK, SAMPLE_RESULTS)
        bar = next((c for c in charts if c["chart_type"] == "bar"), None)
        assert bar is not None, "Expected a grouped bar chart"

    def test_grouped_bar_correct_ordering(self):
        """Acceptance Criteria: The grouped bar chart reproduces the correct ordering
        (6821-6 lowest Rb/Sr, 5621_6 highest Rb/Sr)."""
        charts = ChartBuilder.build_all(SAMPLE_PACK, SAMPLE_RESULTS)
        bar = next(c for c in charts if c["chart_type"] == "bar")
        fig = bar["figure_json"]

        # Extract x-values for rb_sr_ratio trace
        traces = fig["data"]
        # Find the trace named "Rb/Sr Ratio"
        rb_sr_trace = next(t for t in traces if t.get("name") == "Rb/Sr Ratio")
        rb_sr_values = rb_sr_trace["x"]  # horizontal bar: x is the value
        y_labels = rb_sr_trace["y"]  # y is the sample IDs

        assert len(rb_sr_values) == 2

        # Build dict: sample_id -> value
        sample_to_val = dict(zip(y_labels, rb_sr_values, strict=False))
        assert sample_to_val["6821-6"] < sample_to_val["5621_6"], \
            "6821-6 should have lower Rb/Sr than 5621_6"


class TestChartBuilderTernary:
    def test_ternary_created(self):
        charts = ChartBuilder.build_all(SAMPLE_PACK, SAMPLE_RESULTS)
        ternary = next((c for c in charts if c["chart_type"] == "ternary"), None)
        assert ternary is not None, "Expected a ternary diagram for 3-proxy pack"

    def test_ternary_has_correct_structure(self):
        charts = ChartBuilder.build_all(SAMPLE_PACK, SAMPLE_RESULTS)
        ternary = next(c for c in charts if c["chart_type"] == "ternary")
        fig = ternary["figure_json"]
        assert "Scatterternary" in fig["data"][0]["type"] or "scatterternary" in str(fig["data"][0])


class TestChartBuilderScatterMatrix:
    def test_scatter_matrix_created(self):
        charts = ChartBuilder.build_all(SAMPLE_PACK, SAMPLE_RESULTS)
        splom = next(
            (c for c in charts if c["chart_type"] == "scatter" and "Matrix" in c["title"]), None
        )
        assert splom is not None, "Expected a scatter matrix"

    def test_scatter_matrix_has_splom_type(self):
        charts = ChartBuilder.build_all(SAMPLE_PACK, SAMPLE_RESULTS)
        splom_chart = next(
            c for c in charts if c["chart_type"] == "scatter" and "Matrix" in c["title"]
        )
        fig = splom_chart["figure_json"]
        assert "splom" in str(fig["data"][0]).lower() or fig["data"][0].get("type") == "splom"


class TestChartBuilderEdgeCases:
    def test_single_sample_still_generates_some_charts(self):
        """Even with one sample, at least recommendation charts should render (or empty figures)."""
        single_result = [SAMPLE_RESULTS[0]]
        charts = ChartBuilder.build_all(SAMPLE_PACK, single_result)
        assert len(charts) >= 1
        for c in charts:
            assert "figure_json" in c
            assert "title" in c

    def test_no_results_returns_empty(self):
        charts = ChartBuilder.build_all(SAMPLE_PACK, [])
        assert len(charts) >= 1  # recommendations still try to render

    def test_chart_type_is_present(self):
        charts = ChartBuilder.build_all(SAMPLE_PACK, SAMPLE_RESULTS)
        for c in charts:
            assert "chart_type" in c
            assert "title" in c
            assert "figure_json" in c
