"""
Smart Inventory & Sales Analysis System - Analytics Service
------------------------------------------------------------
Phase 9: Fast/Slow-Moving Product Analytics & Sales Velocity

This service layer encapsulates:
1. SQL aggregations for sales transactions and velocity computations.
2. Transparent, data-relative percentile classification (Top 25% Fast, Middle 50% Normal, Bottom 25% Slow).
3. Configurable classification thresholds.
4. Category-level movement and velocity metrics.
5. Store-level sales performance summaries.
6. Support for date range presets (Full Historical Baseline, 30D, 90D, 180D, Custom).

Historical Data Rule:
Source sales records span 2017-01-01 to 2018-09-30 (638 days).
All velocity computations divide by the exact day count of the selected period:
    sales_velocity = total_units_sold / number_of_days_in_period
"""

import datetime
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import db

# ==========================================================
# CONFIGURABLE CLASSIFICATION CONSTANTS
# ==========================================================
DEFAULT_HISTORICAL_START = "2017-01-01"
DEFAULT_HISTORICAL_END = "2018-09-30"

# Percentile cutoffs for relative product movement classification
FAST_PERCENTILE = 0.75  # Top 25% of products by velocity -> FAST MOVING
SLOW_PERCENTILE = 0.25  # Bottom 25% of products by velocity -> SLOW MOVING

def get_analysis_date_bounds() -> Dict[str, Any]:
    """
    Query the minimum and maximum transaction dates available in the sales table.
    Returns default historical boundaries and preset start dates.
    """
    row = db.query_db("""
        SELECT 
            MIN(sale_date) AS min_date,
            MAX(sale_date) AS max_date,
            COUNT(DISTINCT sale_date) AS active_days
        FROM sales;
    """, one=True)

    min_date = row["min_date"] if row and row["min_date"] else DEFAULT_HISTORICAL_START
    max_date = row["max_date"] if row and row["max_date"] else DEFAULT_HISTORICAL_END

    # Compute preset start dates relative to max_date
    try:
        max_dt = datetime.date.fromisoformat(max_date)
        d30_start = (max_dt - datetime.timedelta(days=29)).isoformat()
        d90_start = (max_dt - datetime.timedelta(days=89)).isoformat()
        d180_start = (max_dt - datetime.timedelta(days=179)).isoformat()
    except Exception:
        d30_start = min_date
        d90_start = min_date
        d180_start = min_date

    return {
        "min_date": min_date,
        "max_date": max_date,
        "active_days": row["active_days"] if row else 638,
        "presets": {
            "full": {"start": min_date, "end": max_date, "label": "Full Historical Period"},
            "2017": {"start": "2017-01-01", "end": "2017-12-31", "label": "Year 2017"},
            "2018": {"start": "2018-01-01", "end": max_date, "label": "Year 2018"},
            "30d": {"start": d30_start, "end": max_date, "label": "Last 30 Days"},
            "90d": {"start": d90_start, "end": max_date, "label": "Last 90 Days"},
            "180d": {"start": d180_start, "end": max_date, "label": "Last 180 Days"}
        }
    }

def resolve_date_range(preset: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Tuple[str, str, int, str]:
    """
    Resolves the effective start_date, end_date, day count, and active preset name.
    Guarantees sanitized, valid dates within actual sales bounds.
    """
    bounds = get_analysis_date_bounds()
    presets = bounds["presets"]

    if preset in presets:
        effective_start = presets[preset]["start"]
        effective_end = presets[preset]["end"]
        active_preset = preset
    elif start_date and end_date:
        try:
            s_dt = datetime.date.fromisoformat(start_date)
            e_dt = datetime.date.fromisoformat(end_date)
            if s_dt > e_dt:
                s_dt, e_dt = e_dt, s_dt
            effective_start = s_dt.isoformat()
            effective_end = e_dt.isoformat()
            
            # Check if custom matches an existing preset
            active_preset = "custom"
            for p_key, p_val in presets.items():
                if p_val["start"] == effective_start and p_val["end"] == effective_end:
                    active_preset = p_key
                    break
        except (ValueError, TypeError):
            effective_start = bounds["min_date"]
            effective_end = bounds["max_date"]
            active_preset = "full"
    else:
        effective_start = bounds["min_date"]
        effective_end = bounds["max_date"]
        active_preset = "full"

    # Calculate inclusive days in selected range
    try:
        s_dt = datetime.date.fromisoformat(effective_start)
        e_dt = datetime.date.fromisoformat(effective_end)
        num_days = max(1, (e_dt - s_dt).days + 1)
    except Exception:
        num_days = 638

    return effective_start, effective_end, num_days, active_preset

def calculate_product_velocities(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Executes an optimized SQL aggregation for all active products in the date range.
    Joins sales transaction totals with store inventory snapshot.
    Calculates velocity (units/day) and assigns percentile-based movement status.
    """
    s_dt = datetime.date.fromisoformat(start_date)
    e_dt = datetime.date.fromisoformat(end_date)
    num_days = max(1, (e_dt - s_dt).days + 1)

    # Optimized CTE query joining sales aggregation and inventory totals
    sql = """
        WITH sales_agg AS (
            SELECT 
                s.product_id,
                SUM(s.quantity) AS total_units_sold,
                COUNT(*) AS number_of_transactions,
                ROUND(SUM(s.total_amount), 2) AS calculated_revenue,
                MIN(s.sale_date) AS first_sale_date,
                MAX(s.sale_date) AS last_sale_date
            FROM sales s
            WHERE s.sale_date BETWEEN ? AND ?
            GROUP BY s.product_id
        ),
        inv_agg AS (
            SELECT
                product_id,
                SUM(stock_on_hand) AS current_stock,
                SUM(reorder_level) AS total_reorder_level,
                COUNT(CASE WHEN stock_on_hand = 0 THEN 1 END) AS out_of_stock_stores,
                COUNT(CASE WHEN stock_on_hand > 0 AND stock_on_hand < reorder_level THEN 1 END) AS low_stock_stores
            FROM inventory
            GROUP BY product_id
        )
        SELECT 
            p.product_id,
            p.product_name,
            p.category,
            p.cost_price,
            p.selling_price,
            COALESCE(sa.total_units_sold, 0) AS total_units_sold,
            COALESCE(sa.number_of_transactions, 0) AS number_of_transactions,
            COALESCE(sa.calculated_revenue, 0.0) AS calculated_revenue,
            COALESCE(sa.first_sale_date, 'N/A') AS first_sale_date,
            COALESCE(sa.last_sale_date, 'N/A') AS last_sale_date,
            COALESCE(ia.current_stock, 0) AS current_stock,
            COALESCE(ia.total_reorder_level, 0) AS total_reorder_level,
            COALESCE(ia.out_of_stock_stores, 0) AS out_of_stock_stores,
            COALESCE(ia.low_stock_stores, 0) AS low_stock_stores
        FROM products p
        LEFT JOIN sales_agg sa ON p.product_id = sa.product_id
        LEFT JOIN inv_agg ia ON p.product_id = ia.product_id
        WHERE p.active = 1
        ORDER BY p.product_id ASC;
    """
    raw_products = db.query_db(sql, (start_date, end_date))

    product_list = []
    velocities = []

    for row in raw_products:
        units = row["total_units_sold"]
        txs = row["number_of_transactions"]
        revenue = float(row["calculated_revenue"])
        current_stock = row["current_stock"]
        reorder_level = row["total_reorder_level"]

        # Sales Velocity formula: units sold / total days in period
        velocity = round(units / float(num_days), 2)
        velocities.append(velocity)

        # Average units per transaction
        avg_units_per_tx = round(units / float(txs), 2) if txs > 0 else 0.0

        # Stock health across store network
        if current_stock == 0:
            stock_status = "OUT OF STOCK"
        elif current_stock < reorder_level:
            stock_status = "LOW STOCK"
        else:
            stock_status = "NORMAL"

        product_list.append({
            "product_id": row["product_id"],
            "product_name": row["product_name"],
            "category": row["category"],
            "cost_price": float(row["cost_price"]),
            "selling_price": float(row["selling_price"]),
            "total_units_sold": units,
            "number_of_transactions": txs,
            "calculated_revenue": revenue,
            "sales_velocity": velocity,
            "average_units_per_transaction": avg_units_per_tx,
            "first_sale_date": row["first_sale_date"],
            "last_sale_date": row["last_sale_date"],
            "current_stock": current_stock,
            "total_reorder_level": reorder_level,
            "out_of_stock_stores": row["out_of_stock_stores"],
            "low_stock_stores": row["low_stock_stores"],
            "stock_status": stock_status
        })

    # Transparent Percentile-Based Classification
    if velocities:
        p75 = float(np.percentile(velocities, FAST_PERCENTILE * 100))
        p25 = float(np.percentile(velocities, SLOW_PERCENTILE * 100))
    else:
        p75, p25 = 0.0, 0.0

    # Assign movement classification
    for p in product_list:
        vel = p["sales_velocity"]
        if vel >= p75:
            p["movement_status"] = "FAST MOVING"
            p["movement_badge"] = "badge-emerald"
        elif vel <= p25:
            p["movement_status"] = "SLOW MOVING"
            p["movement_badge"] = "badge-rose"
        else:
            p["movement_status"] = "NORMAL"
            p["movement_badge"] = "badge-indigo"

        p["p75_threshold"] = p75
        p["p25_threshold"] = p25
        p["analysis_days"] = num_days

    return product_list

def get_product_velocity(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    preset: Optional[str] = None,
    movement_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    sort_by: str = "velocity",
    sort_dir: str = "desc"
) -> Dict[str, Any]:
    """
    Primary service method returning classified products, date context, and summary KPIs.
    Supports movement filtering and dynamic multi-column sorting with deterministic tie-breaking.
    """
    effective_start, effective_end, num_days, active_preset = resolve_date_range(preset, start_date, end_date)
    all_products = calculate_product_velocities(effective_start, effective_end)

    # Compute high-level movement summary across all products before table filtering
    summary = get_movement_summary(all_products, num_days, effective_start, effective_end)

    # Filter by movement status if requested
    filtered = all_products
    if movement_filter and movement_filter.lower() != "all":
        mf = movement_filter.strip().lower()
        if mf in ["fast", "fast moving"]:
            filtered = [p for p in filtered if p["movement_status"] == "FAST MOVING"]
        elif mf in ["slow", "slow moving"]:
            filtered = [p for p in filtered if p["movement_status"] == "SLOW MOVING"]
        elif mf in ["normal", "normal moving"]:
            filtered = [p for p in filtered if p["movement_status"] == "NORMAL"]

    # Filter by category if requested
    if category_filter and category_filter.lower() != "all":
        filtered = [p for p in filtered if p["category"].lower() == category_filter.lower()]

    # Deterministic sorting
    reverse = (sort_dir.lower() == "desc")
    if sort_by == "velocity":
        filtered.sort(key=lambda x: (x["sales_velocity"], x["total_units_sold"], x["product_id"]), reverse=reverse)
    elif sort_by == "units":
        filtered.sort(key=lambda x: (x["total_units_sold"], x["sales_velocity"], x["product_id"]), reverse=reverse)
    elif sort_by == "revenue":
        filtered.sort(key=lambda x: (x["calculated_revenue"], x["total_units_sold"], x["product_id"]), reverse=reverse)
    elif sort_by == "name":
        filtered.sort(key=lambda x: x["product_name"].lower(), reverse=reverse)
    elif sort_by == "transactions":
        filtered.sort(key=lambda x: (x["number_of_transactions"], x["total_units_sold"], x["product_id"]), reverse=reverse)
    elif sort_by == "stock":
        filtered.sort(key=lambda x: (x["current_stock"], x["sales_velocity"], x["product_id"]), reverse=reverse)
    else:
        filtered.sort(key=lambda x: (x["sales_velocity"], x["total_units_sold"], x["product_id"]), reverse=True)

    return {
        "start_date": effective_start,
        "end_date": effective_end,
        "num_days": num_days,
        "active_preset": active_preset,
        "summary": summary,
        "products": filtered,
        "total_count": len(filtered)
    }

def get_movement_summary(products: List[Dict[str, Any]], num_days: int, start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Generates high-level KPI aggregation across the product velocity list.
    """
    total_products = len(products)
    total_units = sum(p["total_units_sold"] for p in products)
    total_revenue = round(sum(p["calculated_revenue"] for p in products), 2)
    total_txs = sum(p["number_of_transactions"] for p in products)

    velocities = [p["sales_velocity"] for p in products]
    avg_velocity = round(sum(velocities) / total_products, 2) if total_products > 0 else 0.0

    fast_count = sum(1 for p in products if p["movement_status"] == "FAST MOVING")
    normal_count = sum(1 for p in products if p["movement_status"] == "NORMAL")
    slow_count = sum(1 for p in products if p["movement_status"] == "SLOW MOVING")

    p75 = products[0]["p75_threshold"] if products else 0.0
    p25 = products[0]["p25_threshold"] if products else 0.0

    return {
        "total_products_analyzed": total_products,
        "total_units_sold": total_units,
        "total_revenue": total_revenue,
        "total_transactions": total_txs,
        "average_product_velocity": avg_velocity,
        "fast_moving_count": fast_count,
        "normal_moving_count": normal_count,
        "slow_moving_count": slow_count,
        "fast_threshold_velocity": p75,
        "slow_threshold_velocity": p25,
        "num_days": num_days,
        "start_date": start_date,
        "end_date": end_date
    }

def get_category_analysis(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Aggregates product movement metrics by product category.
    Computes units sold, revenue, average velocity, and movement distributions.
    """
    cat_map: Dict[str, Dict[str, Any]] = {}

    for p in products:
        cat = p["category"]
        if cat not in cat_map:
            cat_map[cat] = {
                "category": cat,
                "product_count": 0,
                "total_units_sold": 0,
                "calculated_revenue": 0.0,
                "velocity_sum": 0.0,
                "fast_count": 0,
                "normal_count": 0,
                "slow_count": 0
            }

        cat_map[cat]["product_count"] += 1
        cat_map[cat]["total_units_sold"] += p["total_units_sold"]
        cat_map[cat]["calculated_revenue"] += p["calculated_revenue"]
        cat_map[cat]["velocity_sum"] += p["sales_velocity"]

        if p["movement_status"] == "FAST MOVING":
            cat_map[cat]["fast_count"] += 1
        elif p["movement_status"] == "SLOW MOVING":
            cat_map[cat]["slow_count"] += 1
        else:
            cat_map[cat]["normal_count"] += 1

    category_list = []
    for cat, data in cat_map.items():
        n = data["product_count"]
        avg_vel = round(data["velocity_sum"] / n, 2) if n > 0 else 0.0
        rev = round(data["calculated_revenue"], 2)

        category_list.append({
            "category": cat,
            "product_count": n,
            "total_units_sold": data["total_units_sold"],
            "calculated_revenue": rev,
            "average_velocity": avg_vel,
            "fast_moving_count": data["fast_count"],
            "normal_moving_count": data["normal_count"],
            "slow_moving_count": data["slow_count"]
        })

    # Sort categories by total units sold descending
    category_list.sort(key=lambda x: x["total_units_sold"], reverse=True)
    return category_list

def get_store_sales_summary(start_date: str, end_date: str, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Calculates store-level sales summaries for the selected period.
    Returns top performing retail store branches.
    """
    sql = """
        WITH store_agg AS (
            SELECT 
                s.store_id,
                SUM(s.quantity) AS total_units_sold,
                COUNT(*) AS number_of_transactions,
                ROUND(SUM(s.total_amount), 2) AS calculated_revenue
            FROM sales s
            WHERE s.sale_date BETWEEN ? AND ?
            GROUP BY s.store_id
        )
        SELECT 
            st.store_id,
            st.store_name,
            st.city,
            st.location,
            COALESCE(sa.total_units_sold, 0) AS units_sold,
            COALESCE(sa.calculated_revenue, 0.0) AS calculated_revenue,
            COALESCE(sa.number_of_transactions, 0) AS transactions
        FROM stores st
        LEFT JOIN store_agg sa ON st.store_id = sa.store_id
        WHERE st.active = 1
        ORDER BY units_sold DESC
        LIMIT ?;
    """
    rows = db.query_db(sql, (start_date, end_date, limit))

    stores = []
    for r in rows:
        stores.append({
            "store_id": r["store_id"],
            "store_name": r["store_name"],
            "city": r["city"],
            "location": r["location"],
            "units_sold": r["units_sold"],
            "calculated_revenue": float(r["calculated_revenue"]),
            "transactions": r["transactions"]
        })
    return stores
