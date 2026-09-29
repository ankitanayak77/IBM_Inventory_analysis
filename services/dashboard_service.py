"""
Smart Inventory & Sales Analysis System - Dashboard Analytics Service
---------------------------------------------------------------------
Phase 11: Interactive Dashboard Charts & Visual Analytics

Provides optimized SQL aggregations for dashboard charts and visual analytics:
1. Sales Trend (Date vs Units Sold)
2. Revenue Trend (Date vs Calculated Revenue)
3. Sales by Category (Units & Revenue)
4. Top 10 Products by Units Sold
5. Inventory Stock Status (Normal, Low Stock, Out of Stock)
6. Inventory Units by Category
7. Store Sales Performance (Units & Revenue with limit selector)
8. Product Movement Distribution (Fast / Normal / Slow from Phase 9)
9. Recommendation Signal Summary (Rule-based counts from Phase 10)

SEMANTICS & DATA INTEGRITY:
- 829,262 sales records are aggregated in SQLite; raw rows are never sent to the browser.
- Historical Sales span: 2017-01-01 to 2018-09-30.
- Current Inventory reflects the live SQLite inventory table state.
- Revenue is calculated (units * catalog selling price).
"""

from typing import Dict, List, Any, Optional
import db
from services import analytics_service, recommendation_service

def get_sales_trend(
    start_date: str,
    end_date: str,
    category: str = "all",
    store_id: str = "all"
) -> Dict[str, Any]:
    """
    Returns daily aggregated sales units and revenue for the given date range.
    Handles empty ranges gracefully.
    """
    conditions = ["s.sale_date >= ?", "s.sale_date <= ?"]
    params: List[Any] = [start_date, end_date]

    if category and category.lower() != "all":
        conditions.append("p.category = ?")
        params.append(category)

    if store_id and str(store_id).lower() != "all":
        try:
            s_id = int(store_id)
            conditions.append("s.store_id = ?")
            params.append(s_id)
        except ValueError:
            pass

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT 
            s.sale_date,
            SUM(s.quantity) AS units_sold,
            ROUND(SUM(s.total_amount), 2) AS calculated_revenue
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        WHERE {where_clause}
        GROUP BY s.sale_date
        ORDER BY s.sale_date ASC;
    """
    rows = db.query_db(sql, params)

    labels = [r["sale_date"] for r in rows]
    units = [int(r["units_sold"]) for r in rows]
    revenue = [float(r["calculated_revenue"]) for r in rows]

    total_units = sum(units)
    total_revenue = round(sum(revenue), 2)

    return {
        "success": True,
        "start_date": start_date,
        "end_date": end_date,
        "labels": labels,
        "units": units,
        "revenue": revenue,
        "total_units": total_units,
        "total_revenue": total_revenue,
        "point_count": len(labels)
    }

def get_revenue_trend(
    start_date: str,
    end_date: str,
    category: str = "all",
    store_id: str = "all"
) -> Dict[str, Any]:
    """
    Returns aggregated revenue trend data.
    Clearly labeled as Calculated Revenue (units * catalog selling price).
    """
    trend_data = get_sales_trend(start_date, end_date, category=category, store_id=store_id)
    return {
        "success": True,
        "start_date": start_date,
        "end_date": end_date,
        "labels": trend_data["labels"],
        "data": trend_data["revenue"],
        "total_revenue": trend_data["total_revenue"],
        "point_count": trend_data["point_count"]
    }

def get_category_sales(
    start_date: str,
    end_date: str,
    store_id: str = "all"
) -> Dict[str, Any]:
    """
    Returns aggregated sales units and revenue grouped by product category.
    Categories are dynamically queried from SQLite.
    """
    conditions = ["s.sale_date >= ?", "s.sale_date <= ?"]
    params: List[Any] = [start_date, end_date]

    if store_id and str(store_id).lower() != "all":
        try:
            s_id = int(store_id)
            conditions.append("s.store_id = ?")
            params.append(s_id)
        except ValueError:
            pass

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT 
            p.category,
            SUM(s.quantity) AS units_sold,
            ROUND(SUM(s.total_amount), 2) AS calculated_revenue,
            COUNT(DISTINCT s.product_id) AS product_count
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        WHERE {where_clause}
        GROUP BY p.category
        ORDER BY units_sold DESC;
    """
    rows = db.query_db(sql, params)

    categories = [r["category"] for r in rows]
    units = [int(r["units_sold"]) for r in rows]
    revenue = [float(r["calculated_revenue"]) for r in rows]

    return {
        "success": True,
        "labels": categories,
        "units": units,
        "revenue": revenue,
        "categories": [dict(r) for r in rows],
        "total_categories": len(categories)
    }

def get_top_products(
    start_date: str,
    end_date: str,
    category: str = "all",
    store_id: str = "all",
    limit: int = 10
) -> Dict[str, Any]:
    """
    Returns top products by units sold in the selected period.
    Sorted descending, limited to top N (default 10).
    """
    conditions = ["s.sale_date >= ?", "s.sale_date <= ?"]
    params: List[Any] = [start_date, end_date]

    if category and category.lower() != "all":
        conditions.append("p.category = ?")
        params.append(category)

    if store_id and str(store_id).lower() != "all":
        try:
            s_id = int(store_id)
            conditions.append("s.store_id = ?")
            params.append(s_id)
        except ValueError:
            pass

    where_clause = " AND ".join(conditions)
    sql = f"""
        SELECT 
            p.product_id,
            p.product_name,
            p.category,
            SUM(s.quantity) AS units_sold,
            ROUND(SUM(s.total_amount), 2) AS calculated_revenue
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        WHERE {where_clause}
        GROUP BY p.product_id, p.product_name, p.category
        ORDER BY units_sold DESC
        LIMIT ?;
    """
    params.append(max(1, int(limit)))
    rows = db.query_db(sql, params)

    labels = [r["product_name"] for r in rows]
    units = [int(r["units_sold"]) for r in rows]
    revenue = [float(r["calculated_revenue"]) for r in rows]

    return {
        "success": True,
        "labels": labels,
        "units": units,
        "revenue": revenue,
        "products": [dict(r) for r in rows]
    }

def get_inventory_status(
    category: str = "all",
    store_id: str = "all"
) -> Dict[str, Any]:
    """
    Returns current inventory counts: NORMAL, LOW STOCK, OUT OF STOCK.
    Evaluated directly against the current SQLite inventory state.
    """
    conditions = []
    params: List[Any] = []

    if category and category.lower() != "all":
        conditions.append("p.category = ?")
        params.append(category)

    if store_id and str(store_id).lower() != "all":
        try:
            s_id = int(store_id)
            conditions.append("i.store_id = ?")
            params.append(s_id)
        except ValueError:
            pass

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT
            COUNT(CASE WHEN i.stock_on_hand >= i.reorder_level THEN 1 END) AS normal_count,
            COUNT(CASE WHEN i.stock_on_hand > 0 AND i.stock_on_hand < i.reorder_level THEN 1 END) AS low_stock_count,
            COUNT(CASE WHEN i.stock_on_hand = 0 THEN 1 END) AS out_of_stock_count,
            COUNT(*) AS total_records,
            COALESCE(SUM(i.stock_on_hand), 0) AS total_units
        FROM inventory i
        JOIN products p ON i.product_id = p.product_id
        {where_clause};
    """
    row = db.query_db(sql, params, one=True)

    normal_count = row["normal_count"] if row else 0
    low_stock_count = row["low_stock_count"] if row else 0
    out_of_stock_count = row["out_of_stock_count"] if row else 0
    total_records = row["total_records"] if row else 0
    total_units = row["total_units"] if row else 0

    return {
        "success": True,
        "labels": ["NORMAL", "LOW STOCK", "OUT OF STOCK"],
        "counts": [normal_count, low_stock_count, out_of_stock_count],
        "colors": ["#10b981", "#f59e0b", "#ef4444"],
        "total_records": total_records,
        "total_units": total_units
    }

def get_inventory_category(store_id: str = "all") -> Dict[str, Any]:
    """
    Returns current inventory units grouped by product category.
    Evaluated from the current SQLite inventory state.
    """
    conditions = []
    params: List[Any] = []

    if store_id and str(store_id).lower() != "all":
        try:
            s_id = int(store_id)
            conditions.append("i.store_id = ?")
            params.append(s_id)
        except ValueError:
            pass

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT 
            p.category,
            COALESCE(SUM(i.stock_on_hand), 0) AS total_units,
            COUNT(DISTINCT p.product_id) AS product_count
        FROM inventory i
        JOIN products p ON i.product_id = p.product_id
        {where_clause}
        GROUP BY p.category
        ORDER BY total_units DESC;
    """
    rows = db.query_db(sql, params)

    labels = [r["category"] for r in rows]
    units = [int(r["total_units"]) for r in rows]

    return {
        "success": True,
        "labels": labels,
        "units": units,
        "categories": [dict(r) for r in rows]
    }

def get_store_sales(
    start_date: str,
    end_date: str,
    category: str = "all",
    limit: Any = 10
) -> Dict[str, Any]:
    """
    Returns top-performing stores by sales units and calculated revenue.
    Supports limit: 5, 10, or 'all'.
    """
    conditions = ["s.sale_date >= ?", "s.sale_date <= ?"]
    params: List[Any] = [start_date, end_date]

    if category and category.lower() != "all":
        conditions.append("p.category = ?")
        params.append(category)

    where_clause = " AND ".join(conditions)

    limit_clause = ""
    if str(limit).lower() != "all":
        try:
            l_val = max(1, int(limit))
            limit_clause = f"LIMIT {l_val}"
        except ValueError:
            limit_clause = "LIMIT 10"

    sql = f"""
        SELECT 
            st.store_id,
            st.store_name,
            st.city,
            SUM(s.quantity) AS units_sold,
            ROUND(SUM(s.total_amount), 2) AS calculated_revenue
        FROM sales s
        JOIN stores st ON s.store_id = st.store_id
        JOIN products p ON s.product_id = p.product_id
        WHERE {where_clause}
        GROUP BY st.store_id, st.store_name, st.city
        ORDER BY units_sold DESC
        {limit_clause};
    """
    rows = db.query_db(sql, params)

    labels = [r["store_name"] for r in rows]
    units = [int(r["units_sold"]) for r in rows]
    revenue = [float(r["calculated_revenue"]) for r in rows]

    return {
        "success": True,
        "labels": labels,
        "units": units,
        "revenue": revenue,
        "stores": [dict(r) for r in rows]
    }

def get_movement_summary(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    preset: Optional[str] = None
) -> Dict[str, Any]:
    """
    Returns distribution of products across FAST MOVING, NORMAL, and SLOW MOVING.
    Reuses existing Phase 9 classification rules without reimplementing logic.
    """
    data = analytics_service.get_product_velocity(
        start_date=start_date,
        end_date=end_date,
        preset=preset
    )
    summary = data["summary"]

    labels = ["FAST MOVING", "NORMAL", "SLOW MOVING"]
    counts = [
        summary["fast_moving_count"],
        summary["normal_moving_count"],
        summary["slow_moving_count"]
    ]

    return {
        "success": True,
        "start_date": data["start_date"],
        "end_date": data["end_date"],
        "num_days": data["num_days"],
        "active_preset": data["active_preset"],
        "labels": labels,
        "counts": counts,
        "colors": ["#10b981", "#6366f1", "#f59e0b"],
        "thresholds": {
            "fast_threshold": summary.get("fast_threshold_velocity", summary.get("fast_threshold", 0.0)),
            "slow_threshold": summary.get("slow_threshold_velocity", summary.get("slow_threshold", 0.0))
        }
    }

def get_recommendation_summary_chart(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    preset: Optional[str] = None
) -> Dict[str, Any]:
    """
    Returns counts for rule-based recommendation signals.
    Reuses existing Phase 10 recommendation engine without duplicating logic.
    """
    data = recommendation_service.get_product_recommendations(
        start_date=start_date,
        end_date=end_date,
        preset=preset
    )
    summary = data["summary"]

    labels = [
        "Prioritize Replenishment",
        "Replenish Soon",
        "Monitor Stock",
        "Review Inventory Level",
        "Replenish or Review",
        "Maintain Current Level",
        "Monitor"
    ]
    counts = [
        summary["prioritize_replenishment_count"],
        summary["replenish_soon_count"],
        summary["monitor_stock_count"],
        summary["review_inventory_level_count"],
        summary["replenish_or_review_count"],
        summary["maintain_current_level_count"],
        summary["monitor_count"]
    ]
    colors = [
        "#e11d48", # Prioritize (Rose)
        "#f43f5e", # Replenish Soon (Rose)
        "#f59e0b", # Monitor Stock (Amber)
        "#d97706", # Review Inventory (Amber)
        "#fbbf24", # Replenish or Review (Amber)
        "#10b981", # Maintain (Emerald)
        "#64748b"  # Monitor (Neutral/Slate)
    ]

    return {
        "success": True,
        "start_date": data["start_date"],
        "end_date": data["end_date"],
        "labels": labels,
        "counts": counts,
        "colors": colors,
        "summary": summary
    }
