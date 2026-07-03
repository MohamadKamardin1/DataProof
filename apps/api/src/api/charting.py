"""Chart builder — transforms AnalysisResult rows + pack definitions into Plotly JSON."""

import base64
import json
from typing import Any

import numpy as np
import plotly.express as px
import plotly.graph_objects as go

from api.models.analysis import AnalysisPack, ChartRecommendation, ProxyResult


def _fig_to_json_safe(fig: go.Figure) -> dict:
    """Serialize a Plotly figure to a plain JSON-safe dict.

    Plotly 6.x uses compact binary array representation internally;
    this ensures the output is plain lists that JSON can serialise.
    """
    raw = json.loads(fig.to_json())
    # Walk the tree and convert compact arrays to lists
    return _decode_plotly_arrays(raw)


def _decode_plotly_arrays(obj: Any) -> Any:
    """Recursively decode Plotly compact arrays ({"dtype": ..., "bdata": ...}) to lists."""
    if isinstance(obj, dict):
        if "dtype" in obj and "bdata" in obj:
            dtype = np.dtype(obj["dtype"])
            decoded = base64.b64decode(obj["bdata"])
            arr = np.frombuffer(decoded, dtype=dtype)
            return arr.tolist()
        return {k: _decode_plotly_arrays(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_decode_plotly_arrays(v) for v in obj]
    return obj


class ChartBuilder:
    """Produces Plotly figure dicts from proxy results and pack chart recommendations."""

    @staticmethod
    def build_all(
        pack: AnalysisPack,
        results: list[ProxyResult],
    ) -> list[dict[str, Any]]:
        """Build all charts for a given pack and its results.

        Returns a list of dicts with keys: figure_json, title, chart_type.
        """
        charts: list[dict[str, Any]] = []

        # 1. Build each chart recommendation from the pack
        for rec in pack.chart_recommendations:
            fig = ChartBuilder._build_from_recommendation(rec, results)
            charts.append({
                "figure_json": fig,
                "title": rec.title,
                "chart_type": rec.type,
            })

        # 2. If there are enough proxies, add a grouped horizontal bar for cross-sample comparison
        if len(results) >= 2:
            bar = ChartBuilder._build_grouped_bar(pack, results)
            if bar is not None:
                charts.append({
                    "figure_json": bar,
                    "title": f"Proxy Comparison — {pack.name}",
                    "chart_type": "bar",
                })

        # 3. If 3+ proxies, add a ternary diagram
        unique_proxies = {r.proxy_id for r in results}
        if len(unique_proxies) >= 3:
            ternary = ChartBuilder._build_ternary(pack, results)
            if ternary is not None:
                charts.append({
                    "figure_json": ternary,
                    "title": "Three-Proxy Ternary Diagram",
                    "chart_type": "ternary",
                })

        # 4. PCA-style scatter matrix for datasets with 3+ measurement columns
        if len(unique_proxies) >= 3:
            scatter_matrix = ChartBuilder._build_scatter_matrix(pack, results)
            if scatter_matrix is not None:
                charts.append({
                    "figure_json": scatter_matrix,
                    "title": "Proxy Scatter Matrix",
                    "chart_type": "scatter",
                })

        return charts

    @staticmethod
    def _build_from_recommendation(
        rec: ChartRecommendation, results: list[ProxyResult]
    ) -> dict:
        """Build a single chart from a pack's chart_recommendation entry."""
        sample_ids = sorted({r.sample_id for r in results})
        x_vals = []
        y_vals = []

        for sid in sample_ids:
            matching = [r for r in results if r.sample_id == sid]
            x_val = None
            y_val = None

            # x_axis could be a column name or a proxy_id
            if rec.x_axis == "sample_id":
                x_val = sid
            else:
                for r in matching:
                    if r.proxy_id == rec.x_axis:
                        x_val = r.value
                        break
                # If no match by proxy_id, treat as column name from measurements
                if x_val is None and matching:
                    for r in matching:
                        if r.label and rec.x_axis.lower() in r.label.lower():
                            x_val = r.value
                            break

            for r in matching:
                if r.proxy_id == rec.y_axis:
                    y_val = r.value
                    break
            if y_val is None and matching:
                for r in matching:
                    if r.label and rec.y_axis.lower() in r.label.lower():
                        y_val = r.value
                        break

            if x_val is not None and y_val is not None:
                x_vals.append(x_val)
                y_vals.append(y_val)

        if not x_vals or not y_vals:
            # Return an empty figure if no valid data points
            fig = go.Figure()
            fig.update_layout(title=rec.title, template="plotly_white")
            return _fig_to_json_safe(fig)

        if rec.type == "bar":
            fig = px.bar(
                x=x_vals, y=y_vals,
                labels={"x": rec.x_axis, "y": rec.y_axis},
                title=rec.title,
            )
            fig.update_layout(
                xaxis_title=rec.x_axis,
                yaxis_title=rec.y_axis,
                template="plotly_white",
            )
        elif rec.type == "scatter":
            fig = px.scatter(
                x=x_vals, y=y_vals,
                text=sample_ids[:len(x_vals)],
                labels={"x": rec.x_axis, "y": rec.y_axis},
                title=rec.title,
            )
            fig.update_traces(textposition="top center")
            fig.update_layout(template="plotly_white")
        else:
            fig = px.line(
                x=sample_ids[:len(x_vals)] if rec.x_axis == "sample_id" else x_vals,
                y=y_vals,
                markers=True,
                labels={"x": rec.x_axis, "y": rec.y_axis},
                title=rec.title,
            )
            fig.update_layout(template="plotly_white")

        return _fig_to_json_safe(fig)

    @staticmethod
    def _build_grouped_bar(pack: AnalysisPack, results: list[ProxyResult]) -> dict | None:
        """Grouped horizontal bar: each sample is a group, each proxy is a bar."""
        sample_ids = sorted({r.sample_id for r in results})
        proxy_ids = sorted({r.proxy_id for r in results})

        if not sample_ids or not proxy_ids:
            return None

        lookup: dict[tuple[str, str], float | None] = {}
        for r in results:
            lookup[(r.sample_id, r.proxy_id)] = r.value

        fig = go.Figure()
        for pid in proxy_ids:
            vals = []
            for sid in sample_ids:
                v = lookup.get((sid, pid))
                vals.append(v if v is not None else 0)
            label = next((r.label for r in results if r.proxy_id == pid), pid)
            fig.add_trace(go.Bar(
                name=label,
                y=sample_ids,
                x=vals,
                orientation="h",
            ))

        fig.update_layout(
            barmode="group",
            title=f"Proxy Comparison — {pack.name}",
            xaxis_title="Value",
            yaxis_title="Sample",
            template="plotly_white",
            height=1200,
            yaxis={"categoryorder": "total ascending"},
            margin={"l": 120, "r": 40, "t": 60, "b": 40},
        )
        return _fig_to_json_safe(fig)

    @staticmethod
    def _build_ternary(pack: AnalysisPack, results: list[ProxyResult]) -> dict | None:
        """Ternary diagram for 3-proxy compositional data.

        Uses the first 3 proxy_ids found in the results.
        """
        sample_ids = sorted({r.sample_id for r in results})
        proxy_ids = sorted({r.proxy_id for r in results})[:3]

        if len(proxy_ids) < 3:
            return None

        lookup: dict[tuple[str, str], float | None] = {}
        for r in results:
            lookup[(r.sample_id, r.proxy_id)] = r.value

        a_vals: list[float] = []
        b_vals: list[float] = []
        c_vals: list[float] = []
        valid_samples: list[str] = []

        for sid in sample_ids:
            av = lookup.get((sid, proxy_ids[0]))
            bv = lookup.get((sid, proxy_ids[1]))
            cv = lookup.get((sid, proxy_ids[2]))
            if av is not None and bv is not None and cv is not None:
                total = av + bv + cv
                if total > 0:
                    a_vals.append(av / total * 100)
                    b_vals.append(bv / total * 100)
                    c_vals.append(cv / total * 100)
                    valid_samples.append(sid)

        if not valid_samples:
            return None

        labels = [
            next((r.label for r in results if r.proxy_id == pid), pid)
            for pid in proxy_ids
        ]

        fig = go.Figure(go.Scatterternary(
            a=a_vals,
            b=b_vals,
            c=c_vals,
            text=valid_samples,
            mode="markers+text",
            textposition="top center",
            marker={"size": 10, "symbol": "circle"},
        ))
        fig.update_layout(
            title="Three-Proxy Ternary Diagram",
            template="plotly_white",
            ternary={
                "aaxis_title": labels[0],
                "baxis_title": labels[1],
                "caxis_title": labels[2],
            },
        )
        return _fig_to_json_safe(fig)

    @staticmethod
    def _build_scatter_matrix(pack: AnalysisPack, results: list[ProxyResult]) -> dict | None:
        """Scatter matrix (splom) for multi-proxy datasets."""
        sample_ids = sorted({r.sample_id for r in results})
        proxy_ids = sorted({r.proxy_id for r in results})

        if len(proxy_ids) < 3:
            return None

        lookup: dict[tuple[str, str], float | None] = {}
        for r in results:
            lookup[(r.sample_id, r.proxy_id)] = r.value

        dims: list[go.splom.Dimension] = []
        for pid in proxy_ids:
            vals = []
            for sid in sample_ids:
                v = lookup.get((sid, pid))
                vals.append(v if v is not None else 0)
            label = next((r.label for r in results if r.proxy_id == pid), pid)
            dims.append(go.splom.Dimension(label=label, values=vals))

        if len(dims) < 2:
            return None

        fig = go.Figure(go.Splom(
            dimensions=dims,
            text=sample_ids,
            marker={"size": 6},
        ))
        fig.update_layout(
            title="Proxy Scatter Matrix",
            template="plotly_white",
            height=500,
            width=700,
        )
        return _fig_to_json_safe(fig)
