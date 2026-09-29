"""
Smart Inventory & Sales Analysis System - Reports & Export Service
------------------------------------------------------------------
Phase 12: Reports & Normalized Power BI Exports

Generates structured, clean, normalized analytical datasets for:
1. Daily Sales Summary (sales_daily.csv)
2. Category Sales Summary (sales_category.csv)
3. Product Movement Classification (product_movement.csv)
4. Store Inventory Snapshot (inventory_snapshot.csv)
5. Store Sales Performance (store_sales.csv)
6. Inventory Recommendations (recommendations.csv)

SEMANTIC RULES & DATA INTEGRITY:
- Tabular, 1 row per logical grain.
- UTF-8 CSV with ISO dates (YYYY-MM-DD).
- Numeric fields remain numeric (no currency symbols or comma formatting).
- Revenue labeled as 'Calculated Revenue' (units * catalog selling price).
- Inventory valuation labeled as 'Calculated Inventory Value at Catalog Selling Price'.
- Historical sales span 2017-01-01 to 2018-09-30.
- Inventory snapshot represents current application state across 50 stores * 35 products.
"""

import io
import csv
from typing import Dict, List, Any, Optional, Tuple
import db
from services import analytics_service, recommendation_service

# ==========================================================
# 1. SALES DAILY REPORT
# ==========================================================
def get_sales_daily_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns daily aggregated sales.
    Columns: sale_date, units_sold, transaction_count, calculated_revenue
    """
    conditions = []
    params: List[Any] = []

    if start_date:
        conditions.append("sale_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("sale_date <= ?")
        params.append(end_date)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT 
            sale_date,
            SUM(quantity) AS units_sold,
            COUNT(*) AS transaction_count,
            ROUND(SUM(total_amount), 2) AS calculated_revenue
        FROM sales
        {where_clause}
        GROUP BY sale_date
        ORDER BY sale_date ASC;
    """
    rows = db.query_db(sql, params)
    return [
        {
            "sale_date": r["sale_date"],
            "units_sold": int(r["units_sold"]),
            "transaction_count": int(r["transaction_count"]),
            "calculated_revenue": float(r["calculated_revenue"])
        }
        for r in rows
    ]

# ==========================================================
# 2. CATEGORY SALES REPORT
# ==========================================================
def get_sales_category_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns aggregated sales by product category.
    Columns: category, units_sold, transaction_count, calculated_revenue, average_units_per_transaction
    """
    conditions = []
    params: List[Any] = []

    if start_date:
        conditions.append("s.sale_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("s.sale_date <= ?")
        params.append(end_date)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT 
            p.category,
            SUM(s.quantity) AS units_sold,
            COUNT(*) AS transaction_count,
            ROUND(SUM(s.total_amount), 2) AS calculated_revenue,
            ROUND(CAST(SUM(s.quantity) AS REAL) / COUNT(*), 2) AS average_units_per_transaction
        FROM sales s
        JOIN products p ON s.product_id = p.product_id
        {where_clause}
        GROUP BY p.category
        ORDER BY units_sold DESC;
    """
    rows = db.query_db(sql, params)
    return [
        {
            "category": r["category"],
            "units_sold": int(r["units_sold"]),
            "transaction_count": int(r["transaction_count"]),
            "calculated_revenue": float(r["calculated_revenue"]),
            "average_units_per_transaction": float(r["average_units_per_transaction"])
        }
        for r in rows
    ]

# ==========================================================
# 3. PRODUCT MOVEMENT REPORT
# ==========================================================
def get_product_movement_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    preset: str = "full"
) -> List[Dict[str, Any]]:
    """
    Returns product movement classification using existing Phase 9 analytics service.
    Columns: product_id, product_name, category, units_sold, transactions,
             sales_velocity, movement_status, current_stock, reorder_level, stock_coverage_days
    """
    analytics_data = analytics_service.get_product_velocity(
        start_date=start_date,
        end_date=end_date,
        preset=preset
    )
    products = analytics_data["products"]

    report_rows = []
    for p in products:
        vel = float(p["sales_velocity"])
        stock = int(p["current_stock"])
        cov = round(stock / vel, 1) if vel > 0 else None

        report_rows.append({
            "product_id": int(p["product_id"]),
            "product_name": p["product_name"],
            "category": p["category"],
            "units_sold": int(p["total_units_sold"]),
            "transactions": int(p["number_of_transactions"]),
            "sales_velocity": vel,
            "movement_status": p["movement_status"],
            "current_stock": stock,
            "reorder_level": int(p.get("total_reorder_level", 500)),
            "stock_coverage_days": cov
        })

    # Sort descending by sales velocity
    report_rows.sort(key=lambda x: (x["sales_velocity"], x["units_sold"], x["product_id"]), reverse=True)
    return report_rows

# ==========================================================
# 4. STORE INVENTORY SNAPSHOT REPORT
# ==========================================================
def get_inventory_snapshot_report() -> List[Dict[str, Any]]:
    """
    Returns current application inventory snapshot across all 50 stores and 35 products.
    Valuation calculated at catalog selling price: stock_on_hand * selling_price.
    Columns: inventory_id, store_id, store_name, city, product_id, product_name,
             category, stock_on_hand, reorder_level, stock_status, inventory_value
    """
    sql = """
        SELECT 
            i.inventory_id,
            st.store_id,
            st.store_name,
            st.city,
            p.product_id,
            p.product_name,
            p.category,
            i.stock_on_hand,
            i.reorder_level,
            p.selling_price
        FROM inventory i
        JOIN stores st ON i.store_id = st.store_id
        JOIN products p ON i.product_id = p.product_id
        ORDER BY st.store_id ASC, p.product_id ASC;
    """
    rows = db.query_db(sql)
    report_rows = []
    for r in rows:
        stock = int(r["stock_on_hand"])
        reorder = int(r["reorder_level"])
        price = float(r["selling_price"])

        if stock == 0:
            status = "OUT OF STOCK"
        elif stock < reorder:
            status = "LOW STOCK"
        else:
            status = "NORMAL"

        inv_val = round(stock * price, 2)

        report_rows.append({
            "inventory_id": int(r["inventory_id"]),
            "store_id": int(r["store_id"]),
            "store_name": r["store_name"],
            "city": r["city"],
            "product_id": int(r["product_id"]),
            "product_name": r["product_name"],
            "category": r["category"],
            "stock_on_hand": stock,
            "reorder_level": reorder,
            "stock_status": status,
            "inventory_value": inv_val
        })

    return report_rows

# ==========================================================
# 5. STORE PERFORMANCE REPORT
# ==========================================================
def get_store_sales_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Returns sales performance across retail store branches.
    Columns: store_id, store_name, city, units_sold, transaction_count, calculated_revenue
    """
    conditions = []
    params: List[Any] = []

    if start_date:
        conditions.append("s.sale_date >= ?")
        params.append(start_date)
    if end_date:
        conditions.append("s.sale_date <= ?")
        params.append(end_date)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    sql = f"""
        SELECT 
            st.store_id,
            st.store_name,
            st.city,
            COALESCE(agg.units_sold, 0) AS units_sold,
            COALESCE(agg.transaction_count, 0) AS transaction_count,
            COALESCE(agg.calculated_revenue, 0.0) AS calculated_revenue
        FROM stores st
        JOIN (
            SELECT 
                s.store_id,
                SUM(s.quantity) AS units_sold,
                COUNT(*) AS transaction_count,
                ROUND(SUM(s.total_amount), 2) AS calculated_revenue
            FROM sales s
            {where_clause}
            GROUP BY s.store_id
        ) agg ON st.store_id = agg.store_id
        ORDER BY units_sold DESC;
    """
    rows = db.query_db(sql, params)
    return [
        {
            "store_id": int(r["store_id"]),
            "store_name": r["store_name"],
            "city": r["city"],
            "units_sold": int(r["units_sold"]),
            "transaction_count": int(r["transaction_count"]),
            "calculated_revenue": float(r["calculated_revenue"])
        }
        for r in rows
    ]

# ==========================================================
# 6. RECOMMENDATIONS REPORT
# ==========================================================
def get_recommendation_report(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    preset: str = "full"
) -> List[Dict[str, Any]]:
    """
    Returns explainable decision-support recommendations using existing Phase 10 engine.
    Columns: product_id, product_name, category, movement_status, current_stock,
             reorder_level, sales_velocity, stock_coverage_days, recommendation, reason, priority
    """
    data = recommendation_service.get_product_recommendations(
        start_date=start_date,
        end_date=end_date,
        preset=preset,
        sort_by="priority",
        sort_dir="asc"
    )
    recs = data["recommendations"]

    report_rows = []
    for r in recs:
        report_rows.append({
            "product_id": int(r["product_id"]),
            "product_name": r["product_name"],
            "category": r["category"],
            "movement_status": r["movement_status"],
            "current_stock": int(r["current_stock"]),
            "reorder_level": int(r.get("total_reorder_level", r.get("reorder_level", 500))),
            "sales_velocity": float(r["sales_velocity"]),
            "stock_coverage_days": r["stock_coverage_days"],
            "recommendation": r["recommendation"],
            "reason": r["reason"],
            "priority": r["priority"],
            "units_sold": int(r.get("total_units_sold", 0)),
            "transactions": int(r.get("number_of_transactions", 0))
        })

    return report_rows

# ==========================================================
# CSV FORMATTER UTILITY
# ==========================================================
def format_csv(rows: List[Dict[str, Any]], fieldnames: List[str]) -> str:
    """
    Converts list of dictionaries to clean, standard UTF-8 CSV string.
    Ensures pure numbers, ISO dates, no currency symbols or commas in numbers.
    """
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        cleaned_row = {}
        for f in fieldnames:
            val = row.get(f)
            if val is None:
                cleaned_row[f] = ""
            elif isinstance(val, float):
                cleaned_row[f] = f"{val:.2f}".rstrip("0").rstrip(".") if "." in f"{val:.2f}" else f"{val:.2f}"
            else:
                cleaned_row[f] = str(val)
        writer.writerow(cleaned_row)
    return output.getvalue()

# ==========================================================
# REPORT SUMMARY KPIS
# ==========================================================
def get_report_summary_kpis(
    sales_daily: Optional[List[Dict[str, Any]]] = None,
    recommendations: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Queries live high-level summary KPIs across sales, catalog, and inventory.
    Accepts precomputed sales_daily and recommendations to avoid redundant table scans.
    """
    if sales_daily is not None and len(sales_daily) > 0:
        total_units = sum(r["units_sold"] for r in sales_daily)
        calculated_revenue = round(sum(r["calculated_revenue"] for r in sales_daily), 2)
        active_days = len(sales_daily)
        transaction_count = sum(r["transaction_count"] for r in sales_daily)
    else:
        sales_kpis = db.query_db("""
            SELECT 
                SUM(quantity) AS total_units,
                ROUND(SUM(total_amount), 2) AS calculated_revenue,
                COUNT(DISTINCT sale_date) AS active_days,
                COUNT(*) AS transaction_count
            FROM sales;
        """, one=True)
        total_units = int(sales_kpis["total_units"] or 0)
        calculated_revenue = float(sales_kpis["calculated_revenue"] or 0.0)
        active_days = int(sales_kpis["active_days"] or 0)
        transaction_count = int(sales_kpis["transaction_count"] or 0)

    prod_count = db.query_db("SELECT COUNT(*) AS c FROM products WHERE active = 1;", one=True)["c"]
    store_count = db.query_db("SELECT COUNT(*) AS c FROM stores WHERE active = 1;", one=True)["c"]

    inv_kpis = db.query_db("""
        SELECT 
            COUNT(CASE WHEN stock_on_hand = 0 THEN 1 END) AS out_of_stock,
            COUNT(CASE WHEN stock_on_hand > 0 AND stock_on_hand < reorder_level THEN 1 END) AS low_stock,
            COUNT(*) AS total_inventory_records,
            COALESCE(SUM(stock_on_hand), 0) AS total_stock
        FROM inventory;
    """, one=True)

    if recommendations is not None:
        attention_count = sum(1 for r in recommendations if r.get("priority") in ("HIGH", "MEDIUM"))
    else:
        rec_data = recommendation_service.get_product_recommendations()
        attention_count = rec_data["summary"]["requires_attention_count"]

    return {
        "total_units_sold": int(total_units),
        "calculated_revenue": float(calculated_revenue),
        "total_transactions": int(transaction_count),
        "active_trading_days": int(active_days),
        "products_analyzed": int(prod_count),
        "stores_analyzed": int(store_count),
        "total_physical_stock": int(inv_kpis["total_stock"] or 0),
        "total_inventory_records": int(inv_kpis["total_inventory_records"] or 0),
        "low_stock_records": int(inv_kpis["low_stock"] or 0),
        "out_of_stock_records": int(inv_kpis["out_of_stock"] or 0),
        "items_requiring_attention": int(attention_count)
    }

