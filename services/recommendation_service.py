"""
Smart Inventory & Sales Analysis System - Recommendation Service
-----------------------------------------------------------------
Phase 10: Rule-Based Inventory Recommendation Engine

Provides transparent, explainable decision-support signals by combining:
1. Product movement status (FAST MOVING, NORMAL, SLOW MOVING)
2. Sales velocity (units / day)
3. Current stock on hand across store network
4. Configured reorder threshold across store network
5. Approximate stock coverage (days) = current_stock / sales_velocity

IMPORTANT PRINCIPLES:
- Recommendations are decision-support signals, NOT machine-learning forecasts.
- Deterministic priority evaluation (Rules 1 through 7).
- Configurable coverage and velocity thresholds.
"""

from typing import Dict, List, Any, Optional
from services import analytics_service

# ==========================================================
# CONFIGURABLE DECISION SUPPORT CONSTANTS
# ==========================================================
# Threshold in days for approximate stock coverage to trigger MONITOR STOCK for fast-moving items
LOW_COVERAGE_THRESHOLD_DAYS = 14.0

PRIORITY_RANKS = {
    "HIGH": 1,
    "MEDIUM": 2,
    "LOW": 3,
    "NONE": 4
}

def evaluate_product_recommendation(
    product: Dict[str, Any],
    low_coverage_threshold: float = LOW_COVERAGE_THRESHOLD_DAYS
) -> Dict[str, Any]:
    """
    Evaluates rule-based recommendation for an individual product in deterministic order.
    
    Rule Evaluation Order:
    1. Fast + Out of Stock -> PRIORITIZE REPLENISHMENT (HIGH)
    2. Fast + Low Stock (< reorder_level) -> REPLENISH SOON (HIGH)
    3. Fast + Healthy Stock (>= reorder_level) + Low Coverage (< 14d) -> MONITOR STOCK (MEDIUM)
    4. Slow + Stock at/above Reorder Level -> REVIEW INVENTORY LEVEL (MEDIUM)
    5. General Out of Stock (Non-Fast) -> REPLENISH OR REVIEW (MEDIUM)
    6. Normal + Healthy Stock (>= reorder_level) -> MAINTAIN CURRENT LEVEL (LOW)
    7. Fallback -> MONITOR (NONE)
    """
    movement = product.get("movement_status", "NORMAL")
    stock = product.get("current_stock", 0)
    reorder = product.get("total_reorder_level", 500)
    velocity = product.get("sales_velocity", 0.0)

    # Calculate approximate stock coverage in days (protect against division by zero)
    if velocity > 0:
        coverage_days = round(stock / float(velocity), 1)
    else:
        coverage_days = None

    # Deterministic Rule Evaluation
    if movement == "FAST MOVING" and stock == 0:
        # RULE 1: Fast Moving + Out of Stock
        rec = "PRIORITIZE REPLENISHMENT"
        reason = "Fast-moving product is currently out of stock."
        priority = "HIGH"
        rec_badge = "badge-rose"
        pri_badge = "badge-rose"

    elif movement == "FAST MOVING" and stock < reorder:
        # RULE 2: Fast Moving + Below Reorder Level
        rec = "REPLENISH SOON"
        reason = "Fast-moving product with stock below the configured reorder level."
        priority = "HIGH"
        rec_badge = "badge-rose"
        pri_badge = "badge-rose"

    elif movement == "FAST MOVING" and stock >= reorder and coverage_days is not None and coverage_days < low_coverage_threshold:
        # RULE 3: Fast Moving + Healthy Stock but Limited Days Coverage
        rec = "MONITOR STOCK"
        reason = f"Product has high sales velocity and limited approximate stock coverage ({coverage_days} days < {low_coverage_threshold}d threshold)."
        priority = "MEDIUM"
        rec_badge = "badge-amber"
        pri_badge = "badge-amber"

    elif movement == "SLOW MOVING" and stock >= reorder:
        # RULE 4: Slow Moving + Stock at/above Reorder Threshold
        rec = "REVIEW INVENTORY LEVEL"
        reason = "Slow-moving product has stock at or above its reorder threshold."
        priority = "MEDIUM"
        rec_badge = "badge-amber"
        pri_badge = "badge-amber"

    elif stock == 0 and movement != "FAST MOVING":
        # RULE 5: General Out of Stock (Non-Fast)
        rec = "REPLENISH OR REVIEW"
        reason = "Product is out of stock; current movement level should be considered before replenishment."
        priority = "MEDIUM"
        rec_badge = "badge-amber"
        pri_badge = "badge-amber"

    elif movement == "NORMAL" and stock >= reorder:
        # RULE 6: Normal Movement + Healthy Stock
        rec = "MAINTAIN CURRENT LEVEL"
        reason = "Current stock is at or above the configured threshold and movement is within the normal range."
        priority = "LOW"
        rec_badge = "badge-emerald"
        pri_badge = "badge-emerald"

    else:
        # RULE 7: Fallback
        rec = "MONITOR"
        reason = "No strong stock or movement signal requires immediate action."
        priority = "NONE"
        rec_badge = "badge-indigo"
        pri_badge = "badge-neutral"

    return {
        "recommendation": rec,
        "reason": reason,
        "priority": priority,
        "priority_rank": PRIORITY_RANKS[priority],
        "stock_coverage_days": coverage_days,
        "rec_badge": rec_badge,
        "pri_badge": pri_badge,
        "low_coverage_threshold": low_coverage_threshold
    }

def get_product_recommendations(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    preset: Optional[str] = None,
    recommendation_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    movement_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    sort_by: str = "priority",
    sort_dir: str = "asc"
) -> Dict[str, Any]:
    """
    Computes rule-based recommendations for all catalog products based on sales velocity
    and inventory stock in the selected analysis period.
    """
    # 1. Reuse existing analytics service
    analytics_data = analytics_service.get_product_velocity(
        start_date=start_date,
        end_date=end_date,
        preset=preset
    )
    raw_products = analytics_data["products"]

    # 2. Evaluate recommendation rules for each product
    all_recommendations = []
    for prod in raw_products:
        rec_info = evaluate_product_recommendation(prod)
        combined = {
            **prod,
            **rec_info,
            "reorder_level": prod.get("total_reorder_level", 0)
        }
        all_recommendations.append(combined)

    # 3. Compute high-level summary KPIs before filtering
    summary = get_recommendation_summary(all_recommendations)

    # 4. Filter by recommendation type
    filtered = all_recommendations
    if recommendation_filter and recommendation_filter.lower() != "all":
        rf = recommendation_filter.strip().lower()
        filtered = [p for p in filtered if p["recommendation"].lower() == rf]

    # Filter by priority
    if priority_filter and priority_filter.lower() != "all":
        pf = priority_filter.strip().upper()
        filtered = [p for p in filtered if p["priority"] == pf]

    # Filter by movement status
    if movement_filter and movement_filter.lower() != "all":
        mf = movement_filter.strip().lower()
        if mf in ["fast", "fast moving"]:
            filtered = [p for p in filtered if p["movement_status"] == "FAST MOVING"]
        elif mf in ["slow", "slow moving"]:
            filtered = [p for p in filtered if p["movement_status"] == "SLOW MOVING"]
        elif mf in ["normal", "normal moving"]:
            filtered = [p for p in filtered if p["movement_status"] == "NORMAL"]

    # Filter by category
    if category_filter and category_filter.lower() != "all":
        filtered = [p for p in filtered if p["category"].lower() == category_filter.lower()]

    # 5. Deterministic sorting
    reverse = (sort_dir.lower() == "desc")
    if sort_by == "priority":
        # Sort by priority rank ascending (HIGH=1 first), then velocity descending
        if not reverse:
            filtered.sort(key=lambda x: (x["priority_rank"], -x["sales_velocity"], x["product_id"]))
        else:
            filtered.sort(key=lambda x: (-x["priority_rank"], x["sales_velocity"], x["product_id"]))
    elif sort_by == "velocity":
        filtered.sort(key=lambda x: (x["sales_velocity"], x["total_units_sold"], x["product_id"]), reverse=reverse)
    elif sort_by == "stock":
        filtered.sort(key=lambda x: (x["current_stock"], x["sales_velocity"], x["product_id"]), reverse=reverse)
    elif sort_by == "coverage":
        # Handle None coverage safely
        filtered.sort(key=lambda x: (x["stock_coverage_days"] if x["stock_coverage_days"] is not None else 999999, x["sales_velocity"]), reverse=reverse)
    elif sort_by == "name":
        filtered.sort(key=lambda x: x["product_name"].lower(), reverse=reverse)
    else:
        filtered.sort(key=lambda x: (x["priority_rank"], -x["sales_velocity"], x["product_id"]))

    return {
        "start_date": analytics_data["start_date"],
        "end_date": analytics_data["end_date"],
        "num_days": analytics_data["num_days"],
        "active_preset": analytics_data["active_preset"],
        "summary": summary,
        "recommendations": filtered,
        "total_count": len(filtered)
    }

def get_recommendation_summary(recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes high-level KPI counts across all evaluated products.
    """
    total = len(recommendations)
    high_count = sum(1 for p in recommendations if p["priority"] == "HIGH")
    medium_count = sum(1 for p in recommendations if p["priority"] == "MEDIUM")
    low_count = sum(1 for p in recommendations if p["priority"] == "LOW")
    none_count = sum(1 for p in recommendations if p["priority"] == "NONE")

    prioritize_replenishment_count = sum(1 for p in recommendations if p["recommendation"] == "PRIORITIZE REPLENISHMENT")
    replenish_soon_count = sum(1 for p in recommendations if p["recommendation"] == "REPLENISH SOON")
    monitor_stock_count = sum(1 for p in recommendations if p["recommendation"] == "MONITOR STOCK")
    review_inventory_count = sum(1 for p in recommendations if p["recommendation"] == "REVIEW INVENTORY LEVEL")
    replenish_or_review_count = sum(1 for p in recommendations if p["recommendation"] == "REPLENISH OR REVIEW")
    maintain_current_count = sum(1 for p in recommendations if p["recommendation"] == "MAINTAIN CURRENT LEVEL")
    monitor_count = sum(1 for p in recommendations if p["recommendation"] == "MONITOR")

    return {
        "total_products": total,
        "requires_attention_count": high_count + medium_count,
        "high_priority_count": high_count,
        "medium_priority_count": medium_count,
        "low_priority_count": low_count,
        "none_priority_count": none_count,
        "prioritize_replenishment_count": prioritize_replenishment_count,
        "replenish_soon_count": replenish_soon_count,
        "monitor_stock_count": monitor_stock_count,
        "review_inventory_level_count": review_inventory_count,
        "replenish_or_review_count": replenish_or_review_count,
        "maintain_current_level_count": maintain_current_count,
        "monitor_count": monitor_count,
        "low_coverage_threshold_days": LOW_COVERAGE_THRESHOLD_DAYS
    }

def get_replenishment_priorities(recommendations: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
    """
    Extracts the highest priority items requiring replenishment or active review.
    """
    actionable = [p for p in recommendations if p["priority"] in ["HIGH", "MEDIUM"]]
    actionable.sort(key=lambda x: (x["priority_rank"], -x["sales_velocity"], x["current_stock"]))
    return actionable[:limit]

def get_product_single_recommendation(product_id: int) -> Dict[str, Any]:
    """
    Evaluates the live recommendation for a single product to display on the Product Detail page.
    """
    data = analytics_service.get_product_velocity()
    matched = [p for p in data["products"] if p["product_id"] == product_id]
    if matched:
        return evaluate_product_recommendation(matched[0])
    return {
        "recommendation": "MONITOR",
        "reason": "Product data currently unavailable for recommendation scoring.",
        "priority": "NONE",
        "priority_rank": 4,
        "stock_coverage_days": None,
        "rec_badge": "badge-indigo",
        "pri_badge": "badge-neutral"
    }
