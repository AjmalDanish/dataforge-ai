"""Executive dashboard engine: a semantic model of the data plus deterministic aggregates.

Everything numeric shown to executives is computed here with pandas; the LLM
(see ``dataforge.llm.brief``) only explains these numbers. The output is plain
JSON so it can be cached, versioned and rendered by the web app.

``infer_model(df)``      -> which columns mean what (revenue, orders, date, dimensions)
``options(model)``       -> the controls a user may choose from (also validates refinements)
``build_dashboard(...)`` -> KPI tiles with period-over-period change, trend, breakdowns,
                            top items and a day x hour heatmap
``facts(dashboard)``     -> the compact fact sheet the LLM is allowed to cite
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd

from dataforge.shared.utils import is_identifier_column, parse_dates_if_mostly_dates

__all__ = ["infer_model", "options", "build_dashboard", "facts", "prepare_frame"]

MONEY_HINTS = ("revenue", "sales", "amount", "total", "price", "value", "gmv")
QTY_HINTS = ("quantity", "qty", "units", "sold", "count")
ORDER_HINTS = ("order", "invoice", "transaction", "receipt", "ticket", "basket", "id")
DATE_HINTS = ("date", "day", "time", "timestamp", "created", "ordered")
GRAINS = ("day", "week", "month")
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MAX_DIM_CARDINALITY = 50


def _hint(name: str, hints: tuple[str, ...]) -> int:
    """Rank of the first hint contained in ``name`` (lower is better), or 99."""
    lowered = str(name).lower()
    return next((i for i, h in enumerate(hints) if h in lowered), 99)


def _is_index_column(s: pd.Series) -> bool:
    """Row numbers exported with the data (``Unnamed: 0``, ``X``, ``index``)."""
    if str(s.name).lower().startswith("unnamed") or str(s.name).lower() == "index":
        return True
    if not pd.api.types.is_integer_dtype(s) or s.isna().any() or len(s) < 3:
        return False
    diffs = s.diff().dropna()
    return bool(s.is_unique and (diffs == 1).all())


def _parse_time_of_day(s: pd.Series) -> pd.Series | None:
    """``11:38:36`` style values -> timedelta since midnight, or None."""
    if not (pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)):
        return None
    sample = s.dropna().astype(str).head(200)
    if sample.empty or not sample.str.match(r"^\d{1,2}:\d{2}(:\d{2})?$").mean() >= 0.8:
        return None
    return pd.to_timedelta(s.astype(str).where(s.astype(str).str.count(":") == 2, s.astype(str) + ":00"), errors="coerce")


def infer_model(df: pd.DataFrame) -> dict[str, Any]:
    """Infer the business meaning of columns. Deterministic; JSON-serialisable."""
    index_cols = [c for c in df.columns if _is_index_column(df[c])]
    cols = [c for c in df.columns if c not in index_cols]
    n = len(df)

    # Date (+ optional separate time-of-day column).
    date_col = time_col = None
    for c in sorted(cols, key=lambda c: _hint(c, DATE_HINTS)):
        s = df[c]
        if pd.api.types.is_datetime64_any_dtype(s) or (
            not pd.api.types.is_numeric_dtype(s) and parse_dates_if_mostly_dates(s) is not None
            and _parse_time_of_day(s) is None
        ):
            date_col = c
            break
    for c in cols:
        if c != date_col and _parse_time_of_day(df[c]) is not None:
            time_col = c
            break
    # A date is a transaction timeline only if events repeat per day; one row per
    # date (product launch dates, birthdays) would make "period over period" nonsense.
    # ponytail: rows-per-date heuristic; add name hints if real data defeats it.
    if date_col is not None and not time_col and n <= df[date_col].nunique(dropna=True) * 1.0:
        date_col = None

    numeric = [
        c for c in cols
        if pd.api.types.is_numeric_dtype(df[c]) and not pd.api.types.is_bool_dtype(df[c])
        and not is_identifier_column(c)
    ]
    money = min(numeric, key=lambda c: _hint(c, MONEY_HINTS), default=None)
    if money is not None and _hint(money, MONEY_HINTS) == 99:
        money = None
    qty = min((c for c in numeric if c != money), key=lambda c: _hint(c, QTY_HINTS), default=None)
    if qty is not None and _hint(qty, QTY_HINTS) == 99:
        qty = None
    # A "revenue/sales/total" column is already line revenue; a price needs quantity.
    revenue_is_line_total = money is not None and _hint(money, MONEY_HINTS) < MONEY_HINTS.index("price")

    # Order key: repeats a little (1-50 rows per value), named like an id/order.
    order_key = None
    for c in sorted(cols, key=lambda c: _hint(c, ORDER_HINTS)):
        if c in (date_col, time_col, money, qty) or _hint(c, ORDER_HINTS) == 99:
            continue
        uniq = df[c].nunique(dropna=True)
        if uniq and 1 <= n / uniq <= 50 and uniq > MAX_DIM_CARDINALITY:
            order_key = c
            break

    taken = {date_col, time_col, money, qty, order_key}
    dimensions = [
        c for c in cols
        if c not in taken and not pd.api.types.is_float_dtype(df[c])
        and 2 <= df[c].nunique(dropna=True) <= MAX_DIM_CARDINALITY
    ]
    # Low-cardinality dimensions first: they make the most readable breakdowns.
    dimensions.sort(key=lambda c: df[c].nunique(dropna=True))

    return {
        "dropped_index_columns": index_cols,
        "date": date_col,
        "time": time_col,
        "money": money,
        "quantity": qty,
        "revenue_is_line_total": revenue_is_line_total,
        "order_key": order_key,
        "dimensions": dimensions,
        "rows": n,
    }


def prepare_frame(df: pd.DataFrame, model: dict[str, Any]) -> pd.DataFrame:
    """Add canonical helper columns: _ts, _revenue, _units."""
    out = df.copy()
    if model["date"]:
        ts = parse_dates_if_mostly_dates(out[model["date"]])
        if ts is None:
            ts = pd.to_datetime(out[model["date"]], errors="coerce")
        ts = ts.dt.normalize() if model["time"] else ts
        if model["time"]:
            ts = ts + _parse_time_of_day(out[model["time"]]).fillna(pd.Timedelta(0))
        out["_ts"] = ts
    qty = pd.to_numeric(out[model["quantity"]], errors="coerce").fillna(0) if model["quantity"] else 1
    if model["money"]:
        money = pd.to_numeric(out[model["money"]], errors="coerce").fillna(0)
        out["_revenue"] = money if model["revenue_is_line_total"] else money * qty
    out["_units"] = qty if model["quantity"] else 1
    return out


def options(model: dict[str, Any], df: pd.DataFrame | None = None) -> dict[str, Any]:
    """Controls a user (or the LLM) may choose from."""
    # Orders and average order value only exist when there is an order key.
    if model["money"]:
        kpis = ["revenue", "orders", "aov", "units"] if model["order_key"] else ["revenue", "units"]
    else:
        kpis = ["records", "orders"] if model["order_key"] else ["records"]
    filters: dict[str, list[str]] = {}
    if df is not None:
        for d in model["dimensions"]:
            filters[d] = sorted(map(str, df[d].dropna().unique()))[:MAX_DIM_CARDINALITY]
    if model["date"]:
        filters["day_type"] = ["weekday", "weekend"]
    return {
        "kpis": kpis,
        "dimensions": list(model["dimensions"]),
        "grains": list(GRAINS) if model["date"] else [],
        "filters": filters,
    }


def _auto_grain(ts: pd.Series) -> str:
    span = (ts.max() - ts.min()).days if ts.notna().any() else 0
    return "month" if span > 90 else "week" if span > 21 else "day"


def _period(ts: pd.Series, grain: str) -> pd.Series:
    return ts.dt.to_period({"day": "D", "week": "W", "month": "M"}[grain])


def _metric_frame(g: pd.core.groupby.DataFrameGroupBy, model: dict[str, Any]) -> pd.DataFrame:
    agg: dict[str, Any] = {"units": ("_units", "sum"), "records": ("_units", "size")}
    if "_revenue" in g.obj:
        agg["revenue"] = ("_revenue", "sum")
    if model["order_key"]:
        agg["orders"] = (model["order_key"], "nunique")
    out = g.agg(**agg)
    if "revenue" in out and "orders" in out:
        out["aov"] = out["revenue"] / out["orders"].replace(0, np.nan)
    return out


def _totals(df: pd.DataFrame, model: dict[str, Any]) -> dict[str, float]:
    t = {"units": float(df["_units"].sum()), "records": float(len(df))}
    if "_revenue" in df:
        t["revenue"] = float(df["_revenue"].sum())
    if model["order_key"]:
        t["orders"] = float(df[model["order_key"]].nunique())
    if "revenue" in t and t.get("orders"):
        t["aov"] = t["revenue"] / t["orders"]
    return t


KPI_LABELS = {
    "revenue": ("Revenue", "currency"),
    "orders": ("Orders", "count"),
    "aov": ("Avg order value", "currency"),
    "units": ("Units sold", "count"),
    "records": ("Records", "count"),
}


def _r(x: Any) -> float | None:
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), 2)


def build_dashboard(
    df: pd.DataFrame, model: dict[str, Any], spec: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Compute the executive dashboard for ``spec`` (validated against ``options``)."""
    spec = dict(spec or {})
    opts = options(model, df)
    frame = prepare_frame(df, model)

    # Validate the spec against what exists; unknown choices are silently dropped.
    kpis = [k for k in spec.get("kpis") or opts["kpis"] if k in opts["kpis"]] or opts["kpis"]
    dims = [d for d in spec.get("dimensions") or opts["dimensions"][:3] if d in opts["dimensions"]]
    filters = {
        k: [v for v in vals if v in opts["filters"].get(k, [])]
        for k, vals in (spec.get("filters") or {}).items()
        if k in opts["filters"]
    }
    filters = {k: v for k, v in filters.items() if v}

    for col, values in filters.items():
        if col == "day_type" and "_ts" in frame:
            weekend = frame["_ts"].dt.dayofweek >= 5
            frame = frame[weekend] if values == ["weekend"] else frame[~weekend] if values == ["weekday"] else frame
        elif col in frame:
            frame = frame[frame[col].astype(str).isin(values)]

    has_time = "_ts" in frame and frame["_ts"].notna().any()
    grain = spec.get("grain") if spec.get("grain") in GRAINS else (_auto_grain(frame["_ts"]) if has_time else None)
    totals = _totals(frame, model)

    trend: list[dict[str, Any]] = []
    current_label = previous_label = None
    by_period = None
    if has_time and grain:
        by_period = _metric_frame(frame.groupby(_period(frame["_ts"], grain)), model)
        trend = [{"period": str(p), **{k: _r(v) for k, v in row.items()}} for p, row in by_period.iterrows()]
        if len(by_period) >= 2:
            current_label, previous_label = str(by_period.index[-1]), str(by_period.index[-2])

    tiles = []
    for k in kpis:
        label, unit = KPI_LABELS[k]
        tile = {"key": k, "label": label, "unit": unit, "value": _r(totals.get(k))}
        if by_period is not None and k in by_period and len(by_period) >= 2:
            cur, prev = by_period[k].iloc[-1], by_period[k].iloc[-2]
            tile.update(
                current=_r(cur),
                previous=_r(prev),
                change_pct=_r((cur - prev) / prev * 100) if prev else None,
                spark=[_r(v) for v in by_period[k].tail(12)],
            )
        tiles.append(tile)

    metric = "revenue" if "_revenue" in frame else "records"
    breakdowns = []
    for d in dims:
        g = _metric_frame(frame.groupby(frame[d].astype(str)), model).sort_values(metric, ascending=False)
        total = g[metric].sum() or np.nan
        rows = [
            {"name": str(i), "value": _r(r[metric]), "share_pct": _r(r[metric] / total * 100),
             **({"orders": _r(r["orders"])} if "orders" in r else {})}
            for i, r in g.head(10).iterrows()
        ]
        breakdowns.append({"dimension": d, "metric": metric, "rows": rows})

    top_items = None
    if model["dimensions"]:
        item = max(model["dimensions"], key=lambda c: df[c].nunique())  # most granular, e.g. product
        g = _metric_frame(frame.groupby(frame[item].astype(str)), model).sort_values(metric, ascending=False)
        top_items = {
            "dimension": item,
            "rows": [
                {"name": str(i), **{k: _r(v) for k, v in r.items() if k != "records"}}
                for i, r in g.head(10).iterrows()
            ],
        }

    heatmap = None
    if has_time and model["time"]:
        ts = frame["_ts"]
        val = frame["_revenue"] if metric == "revenue" else frame["_units"]
        pivot = val.groupby([ts.dt.dayofweek, ts.dt.hour]).sum()
        heatmap = {
            "metric": metric,
            "days": WEEKDAYS,
            "hours": sorted({int(h) for _, h in pivot.index}),
            "cells": [{"day": WEEKDAYS[int(d)], "hour": int(h), "value": _r(v)} for (d, h), v in pivot.items()],
        }

    return {
        "version_spec": {"kpis": kpis, "dimensions": dims, "grain": grain, "filters": filters},
        "model": model,
        "options": opts,
        "date_range": (
            [str(frame["_ts"].min().date()), str(frame["_ts"].max().date())] if has_time else None
        ),
        "period": {"grain": grain, "current": current_label, "previous": previous_label},
        "rows_in_view": int(len(frame)),
        "kpis": tiles,
        "trend": trend,
        "breakdowns": breakdowns,
        "top_items": top_items,
        "heatmap": heatmap,
    }


def facts(dashboard: dict[str, Any]) -> dict[str, Any]:
    """Compact, rounded fact sheet: the only numbers an LLM narrative may cite."""
    out: dict[str, Any] = {
        "date_range": dashboard.get("date_range"),
        "period": dashboard.get("period"),
        "filters": dashboard["version_spec"]["filters"],
        "kpis": [
            {k: t.get(k) for k in ("label", "value", "current", "previous", "change_pct") if t.get(k) is not None}
            for t in dashboard["kpis"]
        ],
        "breakdowns": [
            {"dimension": b["dimension"], "top": b["rows"][:3]} for b in dashboard["breakdowns"]
        ],
    }
    trend = dashboard.get("trend") or []
    key = "revenue" if trend and "revenue" in trend[0] else "records"
    if trend:
        best = max(trend, key=lambda p: p.get(key) or 0)
        worst = min(trend, key=lambda p: p.get(key) or 0)
        out["best_period"] = {"period": best["period"], key: best.get(key)}
        out["worst_period"] = {"period": worst["period"], key: worst.get(key)}
    if dashboard.get("top_items"):
        out["top_items"] = [
            {"name": r["name"], key: r.get(key)} for r in dashboard["top_items"]["rows"][:5]
        ]
    hm = dashboard.get("heatmap")
    if hm and hm["cells"]:
        peak = max(hm["cells"], key=lambda c: c["value"] or 0)
        out["peak_slot"] = {"day": peak["day"], "hour": peak["hour"], hm["metric"]: peak["value"]}
    return out


_NUM = re.compile(r"-?\d[\d,]*\.?\d*")


def numbers_in(text: str) -> list[float]:
    """Numbers as written in prose ('1.2M', '12.5%', '$3,400') -> floats (scaled)."""
    found = []
    for m in re.finditer(r"(-?\d[\d,]*\.?\d*)\s*([kKmMbB])?", text):
        raw = m.group(1).replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        scale = {"k": 1e3, "m": 1e6, "b": 1e9}.get((m.group(2) or "").lower(), 1)
        found.append(v * scale)
    return found


def is_grounded(text: str, fact_sheet: dict[str, Any], tolerance: float = 0.02) -> bool:
    """True when every number in ``text`` matches a number in the fact sheet.

    Small integers (<= 31: counts like "3 recommendations", days, hours) and
    years are allowed; anything else must be within ``tolerance`` (relative)
    of a fact, which covers rounding such as 817,860.05 -> "817.9K".
    """
    known = [abs(x) for x in numbers_in(str(fact_sheet))]
    for v in numbers_in(text):
        v = abs(v)
        if v <= 31 or 1900 <= v <= 2100:
            continue
        if not any(abs(v - k) <= max(tolerance * k, 0.01) for k in known):
            return False
    return True
