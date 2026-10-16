"""Dashboard engine: semantic model, KPIs, period deltas, filters, grounding."""

import numpy as np
import pandas as pd
import pytest

from dataforge.analytics.dashboard import build_dashboard, facts, infer_model, is_grounded, numbers_in


@pytest.fixture
def pizza():
    """Order line items like the real pizza dataset (two months, several pizzas per order)."""
    rng = np.random.default_rng(1)
    rows = []
    order = 0
    for day in pd.date_range("2015-01-01", "2015-02-28"):
        for _ in range(20 if day.month == 1 else 15):
            order += 1
            for _ in range(rng.integers(1, 4)):
                size = rng.choice(["S", "M", "L"])
                rows.append({
                    "date": day.strftime("%Y-%m-%d"),
                    "time": f"{rng.integers(11, 23)}:{rng.integers(0, 60):02d}:00",
                    "id": f"2015-{order:06d}",
                    "name": rng.choice(["hawaiian", "thai_ckn", "bbq_ckn", "veggie"]),
                    "size": size,
                    "type": rng.choice(["classic", "chicken", "veggie"]),
                    "price": {"S": 12.0, "M": 16.0, "L": 20.5}[size],
                })
    df = pd.DataFrame(rows)
    df.insert(0, "Unnamed: 0", range(1, len(df) + 1))
    return df


def test_semantic_model(pizza):
    m = infer_model(pizza)
    assert m["dropped_index_columns"] == ["Unnamed: 0"]
    assert (m["date"], m["time"], m["money"], m["order_key"]) == ("date", "time", "price", "id")
    assert set(m["dimensions"]) == {"size", "type", "name"}


def test_kpis_and_period_change(pizza):
    d = build_dashboard(pizza, infer_model(pizza))
    k = {t["key"]: t for t in d["kpis"]}
    assert k["revenue"]["value"] == round(pizza.price.sum(), 2)
    assert k["orders"]["value"] == pizza.id.nunique()
    assert k["aov"]["value"] == round(pizza.price.sum() / pizza.id.nunique(), 2)
    assert k["units"]["value"] == len(pizza)
    feb = pizza[pizza.date >= "2015-02-01"]
    jan = pizza[pizza.date < "2015-02-01"]
    assert d["period"] == {"grain": "week", "current": d["period"]["current"], "previous": d["period"]["previous"]}
    monthly = build_dashboard(pizza, infer_model(pizza), {"grain": "month"})
    rev = {t["key"]: t for t in monthly["kpis"]}["revenue"]
    assert (rev["current"], rev["previous"]) == (round(feb.price.sum(), 2), round(jan.price.sum(), 2))
    assert rev["change_pct"] == round((feb.price.sum() - jan.price.sum()) / jan.price.sum() * 100, 2)
    assert monthly["heatmap"]["cells"] and monthly["top_items"]["dimension"] == "name"


def test_spec_is_validated_and_filters_apply(pizza):
    m = infer_model(pizza)
    d = build_dashboard(pizza, m, {"kpis": ["revenue", "made_up"], "dimensions": ["size", "nope"],
                                  "filters": {"size": ["L", "XXL"], "bogus": ["x"]}})
    assert d["version_spec"]["kpis"] == ["revenue"]
    assert d["version_spec"]["dimensions"] == ["size"]
    assert d["version_spec"]["filters"] == {"size": ["L"]}
    assert d["kpis"][0]["value"] == round(pizza[pizza["size"] == "L"].price.sum(), 2)
    weekend = build_dashboard(pizza, m, {"filters": {"day_type": ["weekend"]}})
    assert weekend["rows_in_view"] == int((pd.to_datetime(pizza.date).dt.dayofweek >= 5).sum())


def test_generic_data_without_money_or_dates():
    df = pd.DataFrame({"team": ["a", "b", "a", "c"] * 5, "score": range(20)})
    d = build_dashboard(df, infer_model(df))
    assert [t["key"] for t in d["kpis"]] == ["records"]
    assert d["trend"] == [] and d["heatmap"] is None


def test_grounding(pizza):
    fs = facts(build_dashboard(pizza, infer_model(pizza), {"grain": "month"}))
    revenue = fs["kpis"][0]["value"]
    assert is_grounded(f"Revenue reached ${revenue:,.2f} across 3 pizza types in 2015.", fs)
    assert is_grounded(f"Revenue reached {revenue / 1000:.1f}K.", fs)
    assert not is_grounded("Revenue grew 47.3% to $9,999,999.", fs)
    assert numbers_in("1.2M and 12.5% and $3,400") == [1_200_000, 12.5, 3400]


def test_catalog_data_has_no_fake_orders_or_timeline():
    """One row per product with a launch date: no orders/AOV, no period-over-period."""
    df = pd.DataFrame({
        "product_name": [f"p{i}" for i in range(20)],
        "category": ["a", "b"] * 10,
        "price": [10.0 + i for i in range(20)],
        "sold_quantity": [5] * 20,
        "launch_date": pd.date_range("2024-01-01", periods=20, freq="15D").strftime("%Y-%m-%d"),
    })
    m = infer_model(df)
    assert m["date"] is None and m["order_key"] is None
    d = build_dashboard(df, m)
    assert [t["key"] for t in d["kpis"]] == ["revenue", "units"]
    assert d["kpis"][0]["value"] == round(float((df.price * df.sold_quantity).sum()), 2)
    assert d["trend"] == [] and "change_pct" not in d["kpis"][0]
