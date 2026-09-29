"""
Smart Inventory & Sales Analysis System - Main Flask Application
-----------------------------------------------------------------
Phase 4: Flask Application Foundation & SQLite Connection

Connects the normalized SQLite database (database/inventory.db)
with a responsive Jinja2 web frontend.
"""

import math
import datetime
import io
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, abort, jsonify, Response, session
from flask_wtf.csrf import CSRFProtect, CSRFError
from config import Config
import db
from services import analytics_service, recommendation_service, dashboard_service, report_service, auth_service

def create_app(config_class=Config):
    """Application factory for Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize database teardown hooks
    db.init_app(app)
    csrf = CSRFProtect(app)

    # Initialize authentication schema and demo users
    with app.app_context():
        auth_service.init_auth_table()

    # Context processor to inject global variables into templates
    @app.context_processor
    def inject_globals():
        user_id = session.get("user_id")
        current_user = auth_service.get_user_by_id(user_id) if user_id else None
        user_initials = auth_service.get_user_initials(current_user["name"]) if current_user else ""
        return {
            "app_name": app.config.get("APP_NAME", "Smart Inventory System"),
            "app_version": app.config.get("VERSION", "1.0.0"),
            "current_endpoint": request.endpoint,
            "current_user": current_user,
            "user_initials": user_initials
        }

    # ==========================================================
    # ROUTES - AUTHENTICATION (SIGN IN & SIGN UP)
    # ==========================================================

    @app.route("/login", methods=["GET", "POST"])
    def login():
        """User Sign In route."""
        if "user_id" in session:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            email = request.form.get("email")
            password = request.form.get("password")
            remember = bool(request.form.get("remember"))

            res = auth_service.authenticate_user(email, password)
            if res["success"]:
                user = res["user"]
                session.clear()
                session["user_id"] = user["user_id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]
                session["user_role"] = user["role"]
                session.permanent = remember
                flash(f"Welcome back, {user['name']}! Signed in as {user['role']}.", "success")
                next_page = request.args.get("next")
                if next_page and auth_service.is_safe_url(next_page):
                    return redirect(next_page)
                return redirect(url_for("dashboard"))
            else:
                flash(res["message"], "danger")
                return render_template("login.html", email=email), 401

        return render_template("login.html")

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        """User Sign Up / Registration route."""
        if "user_id" in session:
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            password = request.form.get("password")
            confirm_password = request.form.get("confirm_password")

            res = auth_service.register_user(name, email, password, confirm_password)
            if res["success"]:
                user = res["user"]
                session.clear()
                session["user_id"] = user["user_id"]
                session["user_name"] = user["name"]
                session["user_email"] = user["email"]
                session["user_role"] = user["role"]
                flash(res["message"], "success")
                return redirect(url_for("dashboard"))
            else:
                flash(res["message"], "danger")
                return render_template("signup.html", name=name, email=email), 400

        return render_template("signup.html")

    @app.route("/logout")
    def logout():
        """User Sign Out route."""
        user_name = session.get("user_name")
        session.clear()
        if user_name:
            flash(f"Goodbye, {user_name}! You have been signed out successfully.", "info")
        else:
            flash("You have been signed out.", "info")
        return redirect(url_for("login"))

    # ==========================================================
    # ROUTES - USER & ROLE GOVERNANCE (ADMINISTRATOR ONLY)
    # ==========================================================

    @app.route("/admin/users", methods=["GET"])
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN)
    def admin_users():
        """User governance dashboard for system administrators."""
        users_list = auth_service.get_all_users()
        return render_template("admin/users.html", users=users_list)

    @app.route("/admin/users/<int:user_id>/role", methods=["POST"])
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN)
    def admin_update_role(user_id):
        """Update operational role for a user."""
        new_role = request.form.get("role")
        admin_id = session.get("user_id")
        success, msg = auth_service.update_user_role(admin_id, user_id, new_role)
        category = "success" if success else "danger"
        flash(msg, category)
        return redirect(url_for("admin_users"))

    @app.route("/admin/users/<int:user_id>/toggle-status", methods=["POST"])
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN)
    def admin_toggle_status(user_id):
        """Activate or deactivate a user account."""
        admin_id = session.get("user_id")
        success, msg = auth_service.toggle_user_status(admin_id, user_id)
        category = "success" if success else "danger"
        flash(msg, category)
        return redirect(url_for("admin_users"))

    # ==========================================================
    # ROUTES - USER PROFILE & ACCOUNT MANAGEMENT
    # ==========================================================

    @app.route("/profile", methods=["GET"])
    @auth_service.login_required
    def profile():
        """User Profile view displaying account information."""
        user_id = session.get("user_id")
        user = auth_service.get_user_by_id(user_id)
        if not user:
            session.clear()
            flash("User session expired. Please sign in again.", "warning")
            return redirect(url_for("login"))
        user_initials = auth_service.get_user_initials(user["name"])
        return render_template("profile.html", user=user, user_initials=user_initials)

    @app.route("/profile/edit", methods=["GET", "POST"])
    @auth_service.login_required
    def edit_profile():
        """Edit profile personal information (Full Name, Email)."""
        user_id = session.get("user_id")
        user = auth_service.get_user_by_id(user_id)
        if not user:
            session.clear()
            flash("User session expired. Please sign in again.", "warning")
            return redirect(url_for("login"))

        user_initials = auth_service.get_user_initials(user["name"])

        if request.method == "POST":
            name = request.form.get("name")
            email = request.form.get("email")
            current_password = request.form.get("current_password")

            res = auth_service.update_user_profile(user_id, name, email, current_password)
            if res["success"]:
                session["user_name"] = res["user"]["name"]
                session["user_email"] = res["user"]["email"]
                flash(res["message"], "success")
                return redirect(url_for("profile"))
            else:
                flash(res["message"], "danger")
                user_form_state = dict(user)
                user_form_state["name"] = name or ""
                user_form_state["email"] = email or ""
                return render_template(
                    "edit_profile.html",
                    user=user_form_state,
                    user_initials=user_initials
                )

        return render_template("edit_profile.html", user=user, user_initials=user_initials)

    @app.route("/profile/password", methods=["GET", "POST"])
    @auth_service.login_required
    def change_password():
        """Change authenticated user's password."""
        user_id = session.get("user_id")
        user = auth_service.get_user_by_id(user_id)
        if not user:
            session.clear()
            flash("User session expired. Please sign in again.", "warning")
            return redirect(url_for("login"))

        user_initials = auth_service.get_user_initials(user["name"])

        if request.method == "POST":
            current_password = request.form.get("current_password")
            new_password = request.form.get("new_password")
            confirm_password = request.form.get("confirm_password")

            res = auth_service.change_user_password(user_id, current_password, new_password, confirm_password)
            if res["success"]:
                session.clear()
                flash(res["message"], "success")
                return redirect(url_for("login"))
            else:
                flash(res["message"], "danger")
                return render_template("change_password.html", user=user, user_initials=user_initials)

        return render_template("change_password.html", user=user, user_initials=user_initials)

    # ==========================================================
    # ROUTES - DASHBOARD
    # ==========================================================

    @app.route("/")
    @app.route("/dashboard")
    @auth_service.login_required
    def dashboard():
        """
        Dashboard route:
        Queries real SQLite data for all high-level KPIs.
        """
        prod_row = db.query_db("SELECT COUNT(*) AS total FROM products WHERE active = 1;", one=True)
        total_products = prod_row["total"] if prod_row else 0

        store_row = db.query_db("SELECT COUNT(*) AS total FROM stores WHERE active = 1;", one=True)
        total_stores = store_row["total"] if store_row else 0

        sales_summary = db.query_db("""
            SELECT 
                COALESCE(SUM(quantity), 0) AS total_units,
                COALESCE(SUM(total_amount), 0.0) AS calculated_revenue,
                MIN(sale_date) AS min_date,
                MAX(sale_date) AS max_date,
                COUNT(*) AS transaction_count
            FROM sales;
        """, one=True)

        total_units_sold = sales_summary["total_units"] if sales_summary else 0
        calculated_revenue = sales_summary["calculated_revenue"] if sales_summary else 0.0
        min_sale_date = sales_summary["min_date"] if sales_summary else "N/A"
        max_sale_date = sales_summary["max_date"] if sales_summary else "N/A"
        total_transactions = sales_summary["transaction_count"] if sales_summary else 0

        inv_summary = db.query_db("""
            SELECT
                COALESCE(SUM(stock_on_hand), 0) AS total_stock,
                COUNT(CASE WHEN stock_on_hand = 0 THEN 1 END) AS out_of_stock,
                COUNT(CASE WHEN stock_on_hand > 0 AND stock_on_hand < reorder_level THEN 1 END) AS low_stock,
                COUNT(CASE WHEN stock_on_hand >= reorder_level THEN 1 END) AS normal_stock,
                COUNT(*) AS total_inventory_records
            FROM inventory;
        """, one=True)

        total_stock = inv_summary["total_stock"] if inv_summary else 0
        out_of_stock = inv_summary["out_of_stock"] if inv_summary else 0
        low_stock = inv_summary["low_stock"] if inv_summary else 0
        normal_stock = inv_summary["normal_stock"] if inv_summary else 0
        total_inv_records = inv_summary["total_inventory_records"] if inv_summary else 0

        recent_sales = db.query_db("""
            SELECT 
                s.sale_id,
                s.sale_date,
                p.product_name,
                p.category,
                st.store_name,
                st.city,
                s.quantity,
                s.unit_price,
                s.total_amount
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            JOIN stores st ON s.store_id = st.store_id
            ORDER BY s.sale_date DESC, s.sale_id DESC
            LIMIT 6;
        """)

        kpis = {
            "total_products": total_products,
            "total_stores": total_stores,
            "total_units_sold": total_units_sold,
            "calculated_revenue": calculated_revenue,
            "total_transactions": total_transactions,
            "total_stock": total_stock,
            "out_of_stock": out_of_stock,
            "low_stock": low_stock,
            "normal_stock": normal_stock,
            "total_inventory_records": total_inv_records,
            "min_sale_date": min_sale_date,
            "max_sale_date": max_sale_date
        }

        # Rule-based recommendation attention summary for dashboard
        rec_data = recommendation_service.get_product_recommendations()
        attention_summary = rec_data["summary"]
        top_attention_items = recommendation_service.get_replenishment_priorities(rec_data["recommendations"], limit=4)

        bounds = analytics_service.get_analysis_date_bounds()
        cat_rows = db.query_db("SELECT DISTINCT category FROM products ORDER BY category ASC;")
        categories = [r["category"] for r in cat_rows]
        stores = db.query_db("SELECT store_id, store_name, city FROM stores WHERE active = 1 ORDER BY store_name ASC;")

        return render_template(
            "dashboard.html",
            kpis=kpis,
            recent_sales=recent_sales,
            attention_summary=attention_summary,
            top_attention_items=top_attention_items,
            bounds=bounds,
            categories=categories,
            stores=stores
        )

    # ==========================================================
    # ROUTES - PRODUCT CATALOG & CRUD
    # ==========================================================

    @app.route("/products")
    @auth_service.login_required
    def products():
        """
        Product Catalog list view:
        Supports search by name/ID, category filter, and active/inactive filter.
        """
        search_query = request.args.get("search", "").strip()
        category_filter = request.args.get("category", "all").strip()
        status_filter = request.args.get("status", "all").strip().lower()

        # Fetch unique categories for dropdown filter
        cat_rows = db.query_db("SELECT DISTINCT category FROM products ORDER BY category ASC;")
        categories = [r["category"] for r in cat_rows]

        # Build dynamic parameterized query
        conditions = []
        params = []

        if search_query:
            conditions.append("(product_name LIKE ? OR CAST(product_id AS TEXT) LIKE ?)")
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        if category_filter and category_filter != "all":
            conditions.append("category = ?")
            params.append(category_filter)

        if status_filter == "active":
            conditions.append("active = 1")
        elif status_filter == "inactive":
            conditions.append("active = 0")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        sql = f"""
            SELECT 
                product_id,
                product_name,
                category,
                cost_price,
                selling_price,
                active,
                created_at,
                updated_at
            FROM products
            {where_clause}
            ORDER BY product_id ASC;
        """
        raw_products = db.query_db(sql, params)

        # Enhance product objects with calculated margin and margin percentage
        product_list = []
        for p in raw_products:
            cost = float(p["cost_price"])
            price = float(p["selling_price"])
            margin = price - cost
            margin_pct = ((margin / price) * 100) if price > 0 else 0.0

            product_list.append({
                "product_id": p["product_id"],
                "product_name": p["product_name"],
                "category": p["category"],
                "cost_price": cost,
                "selling_price": price,
                "margin": margin,
                "margin_pct": margin_pct,
                "active": p["active"],
                "created_at": p["created_at"],
                "updated_at": p["updated_at"]
            })

        return render_template(
            "products.html",
            products=product_list,
            categories=categories,
            search=search_query,
            selected_category=category_filter,
            selected_status=status_filter,
            total_count=len(product_list)
        )

    @app.route("/products/add", methods=["GET", "POST"])
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN, auth_service.ROLE_MANAGER)
    def add_product():
        """Add new product to catalog."""
        cat_rows = db.query_db("SELECT DISTINCT category FROM products ORDER BY category ASC;")
        existing_categories = [r["category"] for r in cat_rows]

        if request.method == "POST":
            product_name = request.form.get("product_name", "").strip()
            category = request.form.get("category", "").strip()
            new_category = request.form.get("new_category", "").strip()
            cost_str = request.form.get("cost_price", "").strip()
            price_str = request.form.get("selling_price", "").strip()

            # Prefer new category if typed
            final_category = new_category if new_category else category

            # Server-side validation
            errors = []
            if not product_name:
                errors.append("Product name is required.")
            if not final_category:
                errors.append("Category is required.")

            try:
                cost_price = round(float(cost_str), 2)
                if cost_price < 0:
                    errors.append("Cost price cannot be negative.")
            except (ValueError, TypeError):
                errors.append("Valid numeric cost price is required.")
                cost_price = 0.0

            try:
                selling_price = round(float(price_str), 2)
                if selling_price < 0:
                    errors.append("Selling price cannot be negative.")
            except (ValueError, TypeError):
                errors.append("Valid numeric selling price is required.")
                selling_price = 0.0

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template(
                    "add_product.html",
                    existing_categories=existing_categories,
                    product_name=product_name,
                    category=category,
                    new_category=new_category,
                    cost_price=cost_str,
                    selling_price=price_str
                )

            # Insert into SQLite database within atomic transaction
            conn = db.get_db()
            try:
                # Determine next product_id
                cur = conn.cursor()
                cur.execute("SELECT COALESCE(MAX(product_id), 0) + 1 AS next_id FROM products;")
                new_product_id = cur.fetchone()["next_id"]

                cur.execute("""
                    INSERT INTO products (product_id, product_name, category, cost_price, selling_price, active)
                    VALUES (?, ?, ?, ?, ?, 1);
                """, (new_product_id, product_name, final_category, cost_price, selling_price))

                # Initialize inventory records across all 50 stores with 0 stock
                cur.execute("""
                    INSERT OR IGNORE INTO inventory (store_id, product_id, stock_on_hand, reorder_level)
                    SELECT store_id, ?, 0, 10 FROM stores;
                """, (new_product_id,))

                conn.commit()
                flash(f"Product '{product_name}' (ID: #{new_product_id}) added successfully!", "success")
                return redirect(url_for("product_detail", product_id=new_product_id))

            except Exception as e:
                conn.rollback()
                flash(f"Database error while creating product: {str(e)}", "danger")
                return render_template("add_product.html", existing_categories=existing_categories)

        return render_template("add_product.html", existing_categories=existing_categories)

    @app.route("/products/<int:product_id>")
    @auth_service.login_required
    def product_detail(product_id):
        """View individual product details and statistics."""
        product = db.query_db("SELECT * FROM products WHERE product_id = ?;", (product_id,), one=True)
        if not product:
            abort(404)

        cost = float(product["cost_price"])
        price = float(product["selling_price"])
        margin = price - cost
        margin_pct = ((margin / price) * 100) if price > 0 else 0.0

        # Query historical sales summary for this product
        sales_stat = db.query_db("""
            SELECT 
                COALESCE(SUM(quantity), 0) AS total_units_sold,
                COALESCE(SUM(total_amount), 0.0) AS calculated_revenue,
                COUNT(*) AS transaction_count,
                MIN(sale_date) AS first_sale,
                MAX(sale_date) AS last_sale
            FROM sales 
            WHERE product_id = ?;
        """, (product_id,), one=True)

        # Query store inventory summary for this product
        inv_stat = db.query_db("""
            SELECT 
                COALESCE(SUM(stock_on_hand), 0) AS total_stock,
                COUNT(CASE WHEN stock_on_hand > 0 THEN 1 END) AS stores_carrying,
                COUNT(CASE WHEN stock_on_hand = 0 THEN 1 END) AS out_of_stock_stores,
                COUNT(CASE WHEN stock_on_hand > 0 AND stock_on_hand < reorder_level THEN 1 END) AS low_stock_stores
            FROM inventory 
            WHERE product_id = ?;
        """, (product_id,), one=True)

        # Query top store stock levels
        store_inventories = db.query_db("""
            SELECT 
                i.inventory_id,
                i.store_id,
                s.store_name,
                s.city,
                s.location,
                i.stock_on_hand,
                i.reorder_level,
                i.last_updated
            FROM inventory i
            JOIN stores s ON i.store_id = s.store_id
            WHERE i.product_id = ?
            ORDER BY i.stock_on_hand DESC, s.store_name ASC
            LIMIT 15;
        """, (product_id,))

        stats = {
            "margin": margin,
            "margin_pct": margin_pct,
            "total_units_sold": sales_stat["total_units_sold"] if sales_stat else 0,
            "calculated_revenue": sales_stat["calculated_revenue"] if sales_stat else 0.0,
            "transaction_count": sales_stat["transaction_count"] if sales_stat else 0,
            "first_sale": sales_stat["first_sale"] if sales_stat else "N/A",
            "last_sale": sales_stat["last_sale"] if sales_stat else "N/A",
            "total_stock": inv_stat["total_stock"] if inv_stat else 0,
            "stores_carrying": inv_stat["stores_carrying"] if inv_stat else 0,
            "out_of_stock_stores": inv_stat["out_of_stock_stores"] if inv_stat else 0,
            "low_stock_stores": inv_stat["low_stock_stores"] if inv_stat else 0
        }

        # Evaluate live rule-based recommendation for this product
        recommendation = recommendation_service.get_product_single_recommendation(product_id)

        return render_template(
            "product_detail.html",
            product=product,
            stats=stats,
            store_inventories=store_inventories,
            recommendation=recommendation
        )

    @app.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN, auth_service.ROLE_MANAGER)
    def edit_product(product_id):
        """Edit an existing product."""
        product = db.query_db("SELECT * FROM products WHERE product_id = ?;", (product_id,), one=True)
        if not product:
            abort(404)

        cat_rows = db.query_db("SELECT DISTINCT category FROM products ORDER BY category ASC;")
        existing_categories = [r["category"] for r in cat_rows]

        if request.method == "POST":
            product_name = request.form.get("product_name", "").strip()
            category = request.form.get("category", "").strip()
            new_category = request.form.get("new_category", "").strip()
            cost_str = request.form.get("cost_price", "").strip()
            price_str = request.form.get("selling_price", "").strip()

            final_category = new_category if new_category else category

            errors = []
            if not product_name:
                errors.append("Product name is required.")
            if not final_category:
                errors.append("Category is required.")

            try:
                cost_price = round(float(cost_str), 2)
                if cost_price < 0:
                    errors.append("Cost price cannot be negative.")
            except (ValueError, TypeError):
                errors.append("Valid numeric cost price is required.")
                cost_price = 0.0

            try:
                selling_price = round(float(price_str), 2)
                if selling_price < 0:
                    errors.append("Selling price cannot be negative.")
            except (ValueError, TypeError):
                errors.append("Valid numeric selling price is required.")
                selling_price = 0.0

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template(
                    "edit_product.html",
                    product=product,
                    existing_categories=existing_categories
                )

            conn = db.get_db()
            try:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE products 
                    SET product_name = ?, category = ?, cost_price = ?, selling_price = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE product_id = ?;
                """, (product_name, final_category, cost_price, selling_price, product_id))
                conn.commit()

                flash(f"Product '{product_name}' updated successfully!", "success")
                return redirect(url_for("product_detail", product_id=product_id))

            except Exception as e:
                conn.rollback()
                flash(f"Database error while updating product: {str(e)}", "danger")
                return render_template("edit_product.html", product=product, existing_categories=existing_categories)

        return render_template("edit_product.html", product=product, existing_categories=existing_categories)

    @app.route("/products/<int:product_id>/deactivate", methods=["POST"])
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN, auth_service.ROLE_MANAGER)
    def deactivate_product(product_id):
        """Soft-deactivate a product (active = 0). Preserves historical records."""
        product = db.query_db("SELECT * FROM products WHERE product_id = ?;", (product_id,), one=True)
        if not product:
            abort(404)

        conn = db.get_db()
        try:
            conn.execute("UPDATE products SET active = 0, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?;", (product_id,))
            conn.commit()
            flash(f"Product '{product['product_name']}' has been deactivated.", "warning")
        except Exception as e:
            conn.rollback()
            flash(f"Error deactivating product: {str(e)}", "danger")

        return redirect(request.referrer or url_for("products"))

    @app.route("/products/<int:product_id>/activate", methods=["POST"])
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN, auth_service.ROLE_MANAGER)
    def activate_product(product_id):
        """Reactivate a previously deactivated product (active = 1)."""
        product = db.query_db("SELECT * FROM products WHERE product_id = ?;", (product_id,), one=True)
        if not product:
            abort(404)

        conn = db.get_db()
        try:
            conn.execute("UPDATE products SET active = 1, updated_at = CURRENT_TIMESTAMP WHERE product_id = ?;", (product_id,))
            conn.commit()
            flash(f"Product '{product['product_name']}' has been reactivated.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error reactivating product: {str(e)}", "danger")

        return redirect(request.referrer or url_for("products"))

    # ==========================================================
    # ROUTES - INVENTORY MANAGEMENT & STOCK STATUS
    # ==========================================================

    @app.route("/inventory")
    @auth_service.login_required
    def inventory():
        """
        Store Inventory Management & Stock Status overview.
        Provides multi-branch stock tracking, threshold monitoring,
        live stock status categorization, dynamic valuation, and server-side pagination.
        """
        page = request.args.get("page", 1, type=int)
        if page < 1:
            page = 1
        per_page = request.args.get("per_page", 50, type=int)
        if per_page not in [25, 50, 100]:
            per_page = 50

        search_query = request.args.get("search", "").strip()
        product_filter = request.args.get("product_id", "").strip()
        store_filter = request.args.get("store_id", "").strip()
        city_filter = request.args.get("city", "").strip()
        category_filter = request.args.get("category", "").strip()
        stock_status_filter = request.args.get("stock_status", "all").strip().lower()

        # Query options for filter dropdowns
        all_products = db.query_db("SELECT product_id, product_name FROM products ORDER BY product_name ASC;")
        all_stores = db.query_db("SELECT store_id, store_name, city FROM stores ORDER BY store_name ASC;")
        all_cities = db.query_db("SELECT DISTINCT city FROM stores ORDER BY city ASC;")
        all_categories = db.query_db("SELECT DISTINCT category FROM products ORDER BY category ASC;")

        # High-level summary metrics across the enterprise inventory
        summary = db.query_db("""
            SELECT
                COALESCE(SUM(i.stock_on_hand), 0) AS total_units,
                COUNT(CASE WHEN i.stock_on_hand = 0 THEN 1 END) AS out_of_stock,
                COUNT(CASE WHEN i.stock_on_hand > 0 AND i.stock_on_hand < i.reorder_level THEN 1 END) AS low_stock,
                COUNT(CASE WHEN i.stock_on_hand >= i.reorder_level THEN 1 END) AS normal_stock,
                COUNT(*) AS total_records,
                ROUND(COALESCE(SUM(i.stock_on_hand * p.selling_price), 0.0), 2) AS total_inventory_value
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id;
        """, one=True)

        # Build dynamic parameterized query for table
        conditions = []
        params = []

        if search_query:
            conditions.append("(p.product_name LIKE ? OR CAST(p.product_id AS TEXT) LIKE ?)")
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        if product_filter and product_filter != "all":
            try:
                prod_int = int(product_filter)
                conditions.append("i.product_id = ?")
                params.append(prod_int)
            except ValueError:
                pass

        if store_filter and store_filter != "all":
            try:
                store_int = int(store_filter)
                conditions.append("i.store_id = ?")
                params.append(store_int)
            except ValueError:
                pass

        if city_filter and city_filter != "all":
            conditions.append("st.city = ?")
            params.append(city_filter)

        if category_filter and category_filter != "all":
            conditions.append("p.category = ?")
            params.append(category_filter)

        if stock_status_filter == "low":
            conditions.append("(i.stock_on_hand > 0 AND i.stock_on_hand < i.reorder_level)")
        elif stock_status_filter == "out":
            conditions.append("i.stock_on_hand = 0")
        elif stock_status_filter == "normal":
            conditions.append("i.stock_on_hand >= i.reorder_level")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # 1. Total matching count for pagination
        count_sql = f"""
            SELECT COUNT(*) AS total_count
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN stores st ON i.store_id = st.store_id
            {where_clause};
        """
        count_row = db.query_db(count_sql, params, one=True)
        total_count = count_row["total_count"] if count_row else 0

        # Pagination calculations
        total_pages = max(1, math.ceil(total_count / per_page))
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page
        start_index = offset + 1 if total_count > 0 else 0
        end_index = min(offset + per_page, total_count)

        # 2. Paginated rows query
        data_sql = f"""
            SELECT 
                i.inventory_id,
                i.store_id,
                i.product_id,
                i.stock_on_hand,
                i.reorder_level,
                i.last_updated,
                p.product_name,
                p.category,
                p.cost_price,
                p.selling_price,
                st.store_name,
                st.city,
                ROUND(i.stock_on_hand * p.selling_price, 2) AS stock_value,
                CASE 
                    WHEN i.stock_on_hand = 0 THEN 'OUT OF STOCK'
                    WHEN i.stock_on_hand < i.reorder_level THEN 'LOW STOCK'
                    ELSE 'NORMAL'
                END AS stock_status
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN stores st ON i.store_id = st.store_id
            {where_clause}
            ORDER BY 
                p.product_name ASC,
                st.store_name ASC
            LIMIT ? OFFSET ?;
        """
        raw_inventory_records = db.query_db(data_sql, params + [per_page, offset])

        # Attach product-level rule recommendations
        rec_data = recommendation_service.get_product_recommendations()
        rec_map = {p["product_id"]: p for p in rec_data["recommendations"]}

        inventory_records = []
        for r in raw_inventory_records:
            item = dict(r)
            p_rec = rec_map.get(item["product_id"], {})
            item["recommendation"] = p_rec.get("recommendation", "MONITOR")
            item["rec_badge"] = p_rec.get("rec_badge", "badge-indigo")
            item["priority"] = p_rec.get("priority", "NONE")
            inventory_records.append(item)

        return render_template(
            "inventory.html",
            inventory=inventory_records,
            summary=summary,
            all_products=all_products,
            all_stores=all_stores,
            all_cities=all_cities,
            all_categories=all_categories,
            current_page=page,
            total_pages=total_pages,
            per_page=per_page,
            total_count=total_count,
            start_index=start_index,
            end_index=end_index,
            search=search_query,
            selected_product=product_filter,
            selected_store=store_filter,
            selected_city=city_filter,
            selected_category=category_filter,
            selected_status=stock_status_filter
        )

    # ==========================================================
    # ROUTES - SALES MODULE & TRANSACTIONS
    # ==========================================================

    @app.route("/sales")
    @auth_service.login_required
    def sales():
        """
        Sales History list view with server-side pagination and multi-column filtering.
        Handles high-volume datasets (~829k records) with indexed SQL pagination.
        """
        # Parse query params
        page = request.args.get("page", 1, type=int)
        if page < 1:
            page = 1
        per_page = request.args.get("per_page", 50, type=int)
        if per_page not in [25, 50, 100]:
            per_page = 50

        search_query = request.args.get("search", "").strip()
        date_from = request.args.get("date_from", "").strip()
        date_to = request.args.get("date_to", "").strip()
        product_filter = request.args.get("product_id", "").strip()
        store_filter = request.args.get("store_id", "").strip()
        category_filter = request.args.get("category", "").strip()

        # Query options for filter dropdowns
        all_products = db.query_db("SELECT product_id, product_name FROM products ORDER BY product_name ASC;")
        all_stores = db.query_db("SELECT store_id, store_name, city FROM stores ORDER BY store_name ASC;")
        all_categories = db.query_db("SELECT DISTINCT category FROM products ORDER BY category ASC;")

        # Build dynamic SQL conditions
        conditions = []
        params = []

        if search_query:
            conditions.append("(CAST(s.sale_id AS TEXT) LIKE ? OR p.product_name LIKE ?)")
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        if date_from:
            conditions.append("s.sale_date >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("s.sale_date <= ?")
            params.append(date_to)

        if product_filter and product_filter != "all":
            try:
                prod_int = int(product_filter)
                conditions.append("s.product_id = ?")
                params.append(prod_int)
            except ValueError:
                pass

        if store_filter and store_filter != "all":
            try:
                store_int = int(store_filter)
                conditions.append("s.store_id = ?")
                params.append(store_int)
            except ValueError:
                pass

        if category_filter and category_filter != "all":
            conditions.append("p.category = ?")
            params.append(category_filter)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # 1. Count total matching rows
        count_sql = f"""
            SELECT COUNT(*) AS total_count
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            JOIN stores st ON s.store_id = st.store_id
            {where_clause};
        """
        count_row = db.query_db(count_sql, params, one=True)
        total_count = count_row["total_count"] if count_row else 0

        # Pagination calculations
        total_pages = max(1, math.ceil(total_count / per_page))
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page
        start_index = offset + 1 if total_count > 0 else 0
        end_index = min(offset + per_page, total_count)

        # 2. Query paginated slice
        data_sql = f"""
            SELECT 
                s.sale_id,
                s.sale_date,
                s.quantity,
                s.unit_price,
                s.total_amount,
                s.notes,
                s.created_at,
                p.product_id,
                p.product_name,
                p.category,
                st.store_id,
                st.store_name,
                st.city
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            JOIN stores st ON s.store_id = st.store_id
            {where_clause}
            ORDER BY s.sale_date DESC, s.sale_id DESC
            LIMIT ? OFFSET ?;
        """
        sales_records = db.query_db(data_sql, params + [per_page, offset])

        return render_template(
            "sales.html",
            sales=sales_records,
            all_products=all_products,
            all_stores=all_stores,
            all_categories=all_categories,
            current_page=page,
            total_pages=total_pages,
            per_page=per_page,
            total_count=total_count,
            start_index=start_index,
            end_index=end_index,
            search=search_query,
            date_from=date_from,
            date_to=date_to,
            selected_product=product_filter,
            selected_store=store_filter,
            selected_category=category_filter
        )

    @app.route("/sales/add", methods=["GET", "POST"])
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN, auth_service.ROLE_MANAGER, auth_service.ROLE_ASSOCIATE)
    def add_sale():
        """
        Record a new store sale transaction.
        Enforces stock availability checks and atomic inventory & ledger updates.
        """
        active_products = db.query_db("""
            SELECT product_id, product_name, category, selling_price 
            FROM products 
            WHERE active = 1 
            ORDER BY product_name ASC;
        """)
        active_stores = db.query_db("""
            SELECT store_id, store_name, city 
            FROM stores 
            WHERE active = 1 
            ORDER BY store_name ASC;
        """)

        # Default sale date to today
        today_str = datetime.date.today().strftime("%Y-%m-%d")

        if request.method == "POST":
            prod_id_str = request.form.get("product_id", "").strip()
            store_id_str = request.form.get("store_id", "").strip()
            qty_str = request.form.get("quantity", "").strip()
            sale_date = request.form.get("sale_date", "").strip()
            notes = request.form.get("notes", "").strip()

            errors = []

            # 1. Product validation
            try:
                product_id = int(prod_id_str)
                product = db.query_db("SELECT * FROM products WHERE product_id = ?;", (product_id,), one=True)
                if not product:
                    errors.append("Selected product does not exist.")
                elif product["active"] != 1:
                    errors.append(f"Product '{product['product_name']}' is inactive and cannot be sold.")
            except (ValueError, TypeError):
                errors.append("Please select a valid product.")
                product = None

            # 2. Store validation
            try:
                store_id = int(store_id_str)
                store = db.query_db("SELECT * FROM stores WHERE store_id = ?;", (store_id,), one=True)
                if not store:
                    errors.append("Selected store does not exist.")
            except (ValueError, TypeError):
                errors.append("Please select a valid store location.")
                store = None

            # 3. Quantity validation (strictly positive integer)
            try:
                quantity = int(qty_str)
                if quantity <= 0:
                    errors.append("Quantity sold must be at least 1 unit.")
            except (ValueError, TypeError):
                errors.append("Quantity must be a valid positive whole number.")
                quantity = 0

            # 4. Sale date validation
            if not sale_date:
                errors.append("Sale transaction date is required.")
            else:
                try:
                    datetime.date.fromisoformat(sale_date)
                except ValueError:
                    errors.append("Sale date must be in YYYY-MM-DD format.")

            # 5. Inventory Stock Availability Check
            available_stock = 0
            if product and store and quantity > 0:
                inv_row = db.query_db(
                    "SELECT stock_on_hand FROM inventory WHERE store_id = ? AND product_id = ?;",
                    (store_id, product_id),
                    one=True
                )
                available_stock = inv_row["stock_on_hand"] if inv_row else 0
                if available_stock < quantity:
                    errors.append(
                        f"Insufficient stock! Store '{store['store_name']}' has only {available_stock} unit(s) of '{product['product_name']}' available."
                    )

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template(
                    "add_sale.html",
                    active_products=active_products,
                    active_stores=active_stores,
                    today_str=today_str,
                    selected_product_id=prod_id_str,
                    selected_store_id=store_id_str,
                    quantity=qty_str,
                    sale_date=sale_date,
                    notes=notes
                )

            # 6. Atomic Transaction Execution
            unit_price = float(product["selling_price"])
            total_amount = round(quantity * unit_price, 2)
            conn = db.get_db()

            try:
                cur = conn.cursor()

                # Re-verify stock inside transaction
                cur.execute(
                    "SELECT stock_on_hand FROM inventory WHERE store_id = ? AND product_id = ?;",
                    (store_id, product_id)
                )
                current_inv = cur.fetchone()
                current_stock = current_inv["stock_on_hand"] if current_inv else 0
                if current_stock < quantity:
                    raise ValueError(f"Insufficient stock. Only {current_stock} units available.")

                # Generate new sale_id
                cur.execute("SELECT COALESCE(MAX(sale_id), 0) + 1 AS next_id FROM sales;")
                new_sale_id = cur.fetchone()["next_id"]

                # 1. Insert Sales Record
                cur.execute("""
                    INSERT INTO sales (sale_id, product_id, store_id, sale_date, quantity, unit_price, total_amount, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (new_sale_id, product_id, store_id, sale_date, quantity, unit_price, total_amount, notes))

                # 2. Reduce Store Inventory Stock
                cur.execute("""
                    UPDATE inventory
                    SET stock_on_hand = stock_on_hand - ?, last_updated = CURRENT_TIMESTAMP
                    WHERE store_id = ? AND product_id = ?;
                """, (quantity, store_id, product_id))

                # 3. Log Audit Ledger Entry in stock_movements
                movement_notes = f"Sale #{new_sale_id}" + (f" - {notes}" if notes else "")
                cur.execute("""
                    INSERT INTO stock_movements (product_id, store_id, movement_type, quantity, reference_id, movement_date, notes)
                    VALUES (?, ?, 'SALE', ?, ?, CURRENT_TIMESTAMP, ?);
                """, (product_id, store_id, -quantity, new_sale_id, movement_notes))

                conn.commit()

                remaining_stock = current_stock - quantity
                flash(
                    f"Sale #{new_sale_id} recorded successfully! Sold {quantity} &times; '{product['product_name']}' for ${total_amount:,.2f}. Remaining stock at {store['store_name']}: {remaining_stock} units.",
                    "success"
                )
                return redirect(url_for("sale_detail", sale_id=new_sale_id))

            except Exception as e:
                conn.rollback()
                flash(f"Transaction failed: {str(e)}", "danger")
                return render_template(
                    "add_sale.html",
                    active_products=active_products,
                    active_stores=active_stores,
                    today_str=today_str,
                    selected_product_id=prod_id_str,
                    selected_store_id=store_id_str,
                    quantity=qty_str,
                    sale_date=sale_date,
                    notes=notes
                )

        preselected_prod = request.args.get("product_id", "").strip()
        preselected_store = request.args.get("store_id", "").strip()
        return render_template(
            "add_sale.html",
            active_products=active_products,
            active_stores=active_stores,
            today_str=today_str,
            selected_product_id=preselected_prod,
            selected_store_id=preselected_store,
            quantity="1",
            sale_date=today_str,
            notes=""
        )

    @app.route("/sales/<int:sale_id>")
    @auth_service.login_required
    def sale_detail(sale_id):
        """View individual sale transaction details and audit log."""
        sale = db.query_db("""
            SELECT 
                s.sale_id,
                s.sale_date,
                s.quantity,
                s.unit_price,
                s.total_amount,
                s.notes,
                s.created_at,
                p.product_id,
                p.product_name,
                p.category,
                p.cost_price,
                p.selling_price,
                st.store_id,
                st.store_name,
                st.city,
                st.location
            FROM sales s
            JOIN products p ON s.product_id = p.product_id
            JOIN stores st ON s.store_id = st.store_id
            WHERE s.sale_id = ?;
        """, (sale_id,), one=True)

        if not sale:
            abort(404)

        # Current stock remaining for this product at this store
        inv = db.query_db("""
            SELECT stock_on_hand, reorder_level, last_updated
            FROM inventory
            WHERE store_id = ? AND product_id = ?;
        """, (sale["store_id"], sale["product_id"]), one=True)

        # Associated stock movement audit entry
        movement = db.query_db("""
            SELECT movement_id, movement_type, quantity, movement_date, notes
            FROM stock_movements
            WHERE reference_id = ? AND movement_type = 'SALE';
        """, (sale_id,), one=True)

        return render_template("sale_detail.html", sale=sale, inv=inv, movement=movement)

    # ==========================================================
    # JSON API ENDPOINTS
    # ==========================================================

    @app.route("/api/inventory/<int:product_id>/<int:store_id>")
    @auth_service.login_required
    def api_inventory_lookup(product_id, store_id):
        """
        API endpoint returning current stock, pricing, and cost for a product at a store.
        Used by client-side dynamic previews on Sale and Restock forms.
        """
        product = db.query_db(
            "SELECT product_id, product_name, category, cost_price, selling_price, active FROM products WHERE product_id = ?;",
            (product_id,),
            one=True
        )
        store = db.query_db(
            "SELECT store_id, store_name, city FROM stores WHERE store_id = ?;",
            (store_id,),
            one=True
        )

        if not product or not store:
            return jsonify({"success": False, "error": "Product or store not found"}), 404

        inv = db.query_db(
            "SELECT stock_on_hand, reorder_level FROM inventory WHERE product_id = ? AND store_id = ?;",
            (product_id, store_id),
            one=True
        )

        stock_on_hand = inv["stock_on_hand"] if inv else 0
        reorder_level = inv["reorder_level"] if inv else 10

        return jsonify({
            "success": True,
            "product_id": product["product_id"],
            "product_name": product["product_name"],
            "category": product["category"],
            "cost_price": float(product["cost_price"]),
            "selling_price": float(product["selling_price"]),
            "active": product["active"],
            "store_id": store["store_id"],
            "store_name": store["store_name"],
            "city": store["city"],
            "stock_on_hand": stock_on_hand,
            "reorder_level": reorder_level
        })

    @app.route("/api/analytics/product-movement")
    @auth_service.login_required
    def api_analytics_product_movement():
        """
        API endpoint returning product velocity, movement classification, and inventory metrics.
        Supports start_date, end_date, preset, movement, category, sort, and order.
        """
        preset = request.args.get("preset", "full").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None
        movement_filter = request.args.get("movement", "all").strip()
        category_filter = request.args.get("category", "all").strip()
        sort_by = request.args.get("sort", "velocity").strip().lower()
        sort_dir = request.args.get("order", "desc").strip().lower()

        data = analytics_service.get_product_velocity(
            start_date=start_date,
            end_date=end_date,
            preset=preset,
            movement_filter=movement_filter,
            category_filter=category_filter,
            sort_by=sort_by,
            sort_dir=sort_dir
        )
        return jsonify({
            "success": True,
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "num_days": data["num_days"],
            "active_preset": data["active_preset"],
            "summary": data["summary"],
            "total_count": data["total_count"],
            "products": data["products"]
        })

    @app.route("/api/analytics/category-summary")
    @auth_service.login_required
    def api_analytics_category_summary():
        """
        API endpoint returning category-level sales volumes, revenue, velocity, and movement counts.
        """
        preset = request.args.get("preset", "full").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None

        effective_start, effective_end, num_days, active_preset = analytics_service.resolve_date_range(preset, start_date, end_date)
        products = analytics_service.calculate_product_velocities(effective_start, effective_end)
        category_summary = analytics_service.get_category_analysis(products)

        return jsonify({
            "success": True,
            "start_date": effective_start,
            "end_date": effective_end,
            "num_days": num_days,
            "active_preset": active_preset,
            "categories": category_summary
        })

    @app.route("/api/analytics/store-summary")
    @auth_service.login_required
    def api_analytics_store_summary():
        """
        API endpoint returning store-level sales performance for the selected date window.
        """
        preset = request.args.get("preset", "full").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None
        limit = request.args.get("limit", 20, type=int)

        effective_start, effective_end, num_days, active_preset = analytics_service.resolve_date_range(preset, start_date, end_date)
        stores = analytics_service.get_store_sales_summary(effective_start, effective_end, limit=limit)

        return jsonify({
            "success": True,
            "start_date": effective_start,
            "end_date": effective_end,
            "num_days": num_days,
            "active_preset": active_preset,
            "stores": stores
        })

    @app.route("/api/recommendations")
    @auth_service.login_required
    def api_recommendations():
        """
        API endpoint returning rule-based recommendations for all catalog products.
        Supports filtering by recommendation, priority, movement, category, and date range.
        """
        preset = request.args.get("preset", "full").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None
        recommendation_filter = request.args.get("recommendation", "all").strip()
        priority_filter = request.args.get("priority", "all").strip().upper()
        movement_filter = request.args.get("movement", "all").strip().lower()
        category_filter = request.args.get("category", "all").strip()
        sort_by = request.args.get("sort", "priority").strip().lower()
        sort_dir = request.args.get("order", "asc").strip().lower()

        data = recommendation_service.get_product_recommendations(
            start_date=start_date,
            end_date=end_date,
            preset=preset,
            recommendation_filter=recommendation_filter,
            priority_filter=priority_filter,
            movement_filter=movement_filter,
            category_filter=category_filter,
            sort_by=sort_by,
            sort_dir=sort_dir
        )

        return jsonify({
            "success": True,
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "num_days": data["num_days"],
            "active_preset": data["active_preset"],
            "summary": data["summary"],
            "total_count": data["total_count"],
            "recommendations": data["recommendations"]
        })

    @app.route("/api/recommendations/summary")
    @auth_service.login_required
    def api_recommendations_summary():
        """
        API endpoint returning summary counts of rule-based recommendation signals.
        """
        preset = request.args.get("preset", "full").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None

        data = recommendation_service.get_product_recommendations(
            start_date=start_date,
            end_date=end_date,
            preset=preset
        )

        return jsonify({
            "success": True,
            "start_date": data["start_date"],
            "end_date": data["end_date"],
            "num_days": data["num_days"],
            "active_preset": data["active_preset"],
            "summary": data["summary"]
        })

    # ==========================================================
    # ROUTES - PHASE 11: DASHBOARD INTERACTIVE CHARTS & VISUAL ANALYTICS APIS
    # ==========================================================

    @app.route("/api/dashboard/sales-trend")
    @auth_service.login_required
    def api_dashboard_sales_trend():
        """
        API Endpoint: Daily sales units trend.
        Accepts preset, start_date, end_date, category, store_id.
        """
        preset = request.args.get("preset", "").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None
        if not preset:
            preset = "custom" if (start_date and end_date) else "full"
        category = request.args.get("category", "all").strip()
        store_id = request.args.get("store_id", "all").strip()

        s_date, e_date, num_days, active_preset = analytics_service.resolve_date_range(preset, start_date, end_date)
        data = dashboard_service.get_sales_trend(s_date, e_date, category=category, store_id=store_id)
        data["active_preset"] = active_preset
        data["num_days"] = num_days
        return jsonify(data)

    @app.route("/api/dashboard/revenue-trend")
    @auth_service.login_required
    def api_dashboard_revenue_trend():
        """
        API Endpoint: Daily calculated revenue trend (units * catalog selling price).
        Accepts preset, start_date, end_date, category, store_id.
        """
        preset = request.args.get("preset", "").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None
        if not preset:
            preset = "custom" if (start_date and end_date) else "full"
        category = request.args.get("category", "all").strip()
        store_id = request.args.get("store_id", "all").strip()

        s_date, e_date, num_days, active_preset = analytics_service.resolve_date_range(preset, start_date, end_date)
        data = dashboard_service.get_revenue_trend(s_date, e_date, category=category, store_id=store_id)
        data["active_preset"] = active_preset
        data["num_days"] = num_days
        return jsonify(data)

    @app.route("/api/dashboard/category-sales")
    @auth_service.login_required
    def api_dashboard_category_sales():
        """
        API Endpoint: Sales units and calculated revenue by product category.
        Accepts preset, start_date, end_date, store_id.
        """
        preset = request.args.get("preset", "").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None
        if not preset:
            preset = "custom" if (start_date and end_date) else "full"
        store_id = request.args.get("store_id", "all").strip()

        s_date, e_date, num_days, active_preset = analytics_service.resolve_date_range(preset, start_date, end_date)
        data = dashboard_service.get_category_sales(s_date, e_date, store_id=store_id)
        data["active_preset"] = active_preset
        data["num_days"] = num_days
        return jsonify(data)

    @app.route("/api/dashboard/top-products")
    @auth_service.login_required
    def api_dashboard_top_products():
        """
        API Endpoint: Top products by units sold in the selected period.
        Accepts preset, start_date, end_date, category, store_id, limit (default 10).
        """
        preset = request.args.get("preset", "").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None
        if not preset:
            preset = "custom" if (start_date and end_date) else "full"
        category = request.args.get("category", "all").strip()
        store_id = request.args.get("store_id", "all").strip()
        limit = request.args.get("limit", 10)

        s_date, e_date, num_days, active_preset = analytics_service.resolve_date_range(preset, start_date, end_date)
        data = dashboard_service.get_top_products(s_date, e_date, category=category, store_id=store_id, limit=limit)
        data["active_preset"] = active_preset
        data["num_days"] = num_days
        return jsonify(data)

    @app.route("/api/dashboard/inventory-status")
    @auth_service.login_required
    def api_dashboard_inventory_status():
        """
        API Endpoint: Current inventory counts (NORMAL, LOW STOCK, OUT OF STOCK).
        Evaluated against the current SQLite inventory state.
        """
        category = request.args.get("category", "all").strip()
        store_id = request.args.get("store_id", "all").strip()

        data = dashboard_service.get_inventory_status(category=category, store_id=store_id)
        return jsonify(data)

    @app.route("/api/dashboard/inventory-category")
    @auth_service.login_required
    def api_dashboard_inventory_category():
        """
        API Endpoint: Current inventory units grouped by category.
        Evaluated against the current SQLite inventory state.
        """
        store_id = request.args.get("store_id", "all").strip()

        data = dashboard_service.get_inventory_category(store_id=store_id)
        return jsonify(data)

    @app.route("/api/dashboard/store-sales")
    @auth_service.login_required
    def api_dashboard_store_sales():
        """
        API Endpoint: Sales performance by store branch.
        Accepts preset, start_date, end_date, category, limit (5, 10, or 'all', default 10).
        """
        preset = request.args.get("preset", "").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None
        if not preset:
            preset = "custom" if (start_date and end_date) else "full"
        category = request.args.get("category", "all").strip()
        limit = request.args.get("limit", 10)

        s_date, e_date, num_days, active_preset = analytics_service.resolve_date_range(preset, start_date, end_date)
        data = dashboard_service.get_store_sales(s_date, e_date, category=category, limit=limit)
        data["active_preset"] = active_preset
        data["num_days"] = num_days
        return jsonify(data)

    @app.route("/api/dashboard/movement-summary")
    @auth_service.login_required
    def api_dashboard_movement_summary():
        """
        API Endpoint: Product movement distribution (FAST MOVING, NORMAL, SLOW MOVING).
        Consumes Phase 9 analytics service classification.
        """
        preset = request.args.get("preset", "").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None
        if not preset:
            preset = "custom" if (start_date and end_date) else "full"

        data = dashboard_service.get_movement_summary(start_date=start_date, end_date=end_date, preset=preset)
        return jsonify(data)

    @app.route("/api/dashboard/recommendation-summary")
    @auth_service.login_required
    def api_dashboard_recommendation_summary():
        """
        API Endpoint: Counts for rule-based recommendation signals.
        Consumes Phase 10 recommendation service.
        """
        preset = request.args.get("preset", "").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None
        if not preset:
            preset = "custom" if (start_date and end_date) else "full"
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None

        data = dashboard_service.get_recommendation_summary_chart(start_date=start_date, end_date=end_date, preset=preset)
        return jsonify(data)

    # ==========================================================
    # ROUTES - RESTOCK MODULE & INBOUND INVENTORY
    # ==========================================================

    @app.route("/restock")
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN, auth_service.ROLE_MANAGER)
    def restock():
        """
        Restock History list view with filtering and server-side pagination.
        Shows replenishment orders across retail store branches.
        """
        page = request.args.get("page", 1, type=int)
        if page < 1:
            page = 1
        per_page = request.args.get("per_page", 50, type=int)
        if per_page not in [25, 50, 100]:
            per_page = 50

        search_query = request.args.get("search", "").strip()
        date_from = request.args.get("date_from", "").strip()
        date_to = request.args.get("date_to", "").strip()
        product_filter = request.args.get("product_id", "").strip()
        store_filter = request.args.get("store_id", "").strip()
        category_filter = request.args.get("category", "").strip()

        all_products = db.query_db("SELECT product_id, product_name FROM products ORDER BY product_name ASC;")
        all_stores = db.query_db("SELECT store_id, store_name, city FROM stores ORDER BY store_name ASC;")
        all_categories = db.query_db("SELECT DISTINCT category FROM products ORDER BY category ASC;")

        conditions = []
        params = []

        if search_query:
            conditions.append("(CAST(r.restock_id AS TEXT) LIKE ? OR p.product_name LIKE ?)")
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        if date_from:
            conditions.append("r.restock_date >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("r.restock_date <= ?")
            params.append(date_to)

        if product_filter and product_filter != "all":
            try:
                prod_int = int(product_filter)
                conditions.append("r.product_id = ?")
                params.append(prod_int)
            except ValueError:
                pass

        if store_filter and store_filter != "all":
            try:
                store_int = int(store_filter)
                conditions.append("r.store_id = ?")
                params.append(store_int)
            except ValueError:
                pass

        if category_filter and category_filter != "all":
            conditions.append("p.category = ?")
            params.append(category_filter)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        count_sql = f"""
            SELECT COUNT(*) AS total_count
            FROM restocks r
            JOIN products p ON r.product_id = p.product_id
            JOIN stores st ON r.store_id = st.store_id
            {where_clause};
        """
        count_row = db.query_db(count_sql, params, one=True)
        total_count = count_row["total_count"] if count_row else 0

        total_pages = max(1, math.ceil(total_count / per_page))
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * per_page
        start_index = offset + 1 if total_count > 0 else 0
        end_index = min(offset + per_page, total_count)

        data_sql = f"""
            SELECT 
                r.restock_id,
                r.restock_date,
                r.quantity,
                r.cost_per_unit,
                ROUND(r.quantity * r.cost_per_unit, 2) AS total_cost,
                r.notes,
                r.created_at,
                p.product_id,
                p.product_name,
                p.category,
                st.store_id,
                st.store_name,
                st.city
            FROM restocks r
            JOIN products p ON r.product_id = p.product_id
            JOIN stores st ON r.store_id = st.store_id
            {where_clause}
            ORDER BY r.restock_date DESC, r.restock_id DESC
            LIMIT ? OFFSET ?;
        """
        restock_records = db.query_db(data_sql, params + [per_page, offset])

        return render_template(
            "restock.html",
            restocks=restock_records,
            all_products=all_products,
            all_stores=all_stores,
            all_categories=all_categories,
            current_page=page,
            total_pages=total_pages,
            per_page=per_page,
            total_count=total_count,
            start_index=start_index,
            end_index=end_index,
            search=search_query,
            date_from=date_from,
            date_to=date_to,
            selected_product=product_filter,
            selected_store=store_filter,
            selected_category=category_filter
        )

    @app.route("/restock/add", methods=["GET", "POST"])
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN, auth_service.ROLE_MANAGER)
    def add_restock():
        """
        Record a new store restock (inbound inventory replenishment).
        Increases store stock and logs RESTOCK movement in atomic transaction.
        """
        active_products = db.query_db("""
            SELECT product_id, product_name, category, cost_price, selling_price 
            FROM products 
            WHERE active = 1 
            ORDER BY product_name ASC;
        """)
        active_stores = db.query_db("""
            SELECT store_id, store_name, city 
            FROM stores 
            WHERE active = 1 
            ORDER BY store_name ASC;
        """)

        today_str = datetime.date.today().strftime("%Y-%m-%d")

        if request.method == "POST":
            prod_id_str = request.form.get("product_id", "").strip()
            store_id_str = request.form.get("store_id", "").strip()
            qty_str = request.form.get("quantity", "").strip()
            cost_str = request.form.get("cost_per_unit", "").strip()
            restock_date = request.form.get("restock_date", "").strip()
            notes = request.form.get("notes", "").strip()

            errors = []

            # 1. Product validation
            try:
                product_id = int(prod_id_str)
                product = db.query_db("SELECT * FROM products WHERE product_id = ?;", (product_id,), one=True)
                if not product:
                    errors.append("Selected product does not exist.")
                elif product["active"] != 1:
                    errors.append(f"Product '{product['product_name']}' is inactive and cannot be restocked.")
            except (ValueError, TypeError):
                errors.append("Please select a valid product.")
                product = None

            # 2. Store validation
            try:
                store_id = int(store_id_str)
                store = db.query_db("SELECT * FROM stores WHERE store_id = ?;", (store_id,), one=True)
                if not store:
                    errors.append("Selected store does not exist.")
            except (ValueError, TypeError):
                errors.append("Please select a valid store location.")
                store = None

            # 3. Inventory row existence check
            inv_row = None
            if product and store:
                inv_row = db.query_db(
                    "SELECT stock_on_hand, reorder_level FROM inventory WHERE store_id = ? AND product_id = ?;",
                    (store_id, product_id),
                    one=True
                )
                if not inv_row:
                    errors.append(f"Inventory record missing for {product['product_name']} at {store['store_name']}.")

            # 4. Quantity validation (strictly positive integer)
            try:
                quantity = int(qty_str)
                if quantity <= 0:
                    errors.append("Restock quantity must be at least 1 unit.")
            except (ValueError, TypeError):
                errors.append("Quantity must be a valid positive whole number.")
                quantity = 0

            # 5. Cost per unit validation (>= 0)
            try:
                cost_per_unit = round(float(cost_str), 2)
                if cost_per_unit < 0:
                    errors.append("Cost per unit cannot be negative.")
            except (ValueError, TypeError):
                errors.append("Please provide a valid numeric cost per unit.")
                cost_per_unit = 0.0

            # 6. Date validation
            if not restock_date:
                errors.append("Restock transaction date is required.")
            else:
                try:
                    datetime.date.fromisoformat(restock_date)
                except ValueError:
                    errors.append("Restock date must be in YYYY-MM-DD format.")

            if errors:
                for err in errors:
                    flash(err, "danger")
                return render_template(
                    "add_restock.html",
                    active_products=active_products,
                    active_stores=active_stores,
                    today_str=today_str,
                    selected_product_id=prod_id_str,
                    selected_store_id=store_id_str,
                    quantity=qty_str,
                    cost_per_unit=cost_str,
                    restock_date=restock_date,
                    notes=notes
                )

            # 7. Atomic Transaction Execution
            total_cost = round(quantity * cost_per_unit, 2)
            conn = db.get_db()

            try:
                cur = conn.cursor()

                # Verify current inventory stock
                cur.execute(
                    "SELECT stock_on_hand FROM inventory WHERE store_id = ? AND product_id = ?;",
                    (store_id, product_id)
                )
                current_inv = cur.fetchone()
                current_stock = current_inv["stock_on_hand"] if current_inv else 0

                # 1. Insert Restocks Record
                cur.execute("""
                    INSERT INTO restocks (product_id, store_id, quantity, cost_per_unit, restock_date, notes)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (product_id, store_id, quantity, cost_per_unit, restock_date, notes))
                new_restock_id = cur.lastrowid

                # 2. Increase Inventory Stock
                cur.execute("""
                    UPDATE inventory
                    SET stock_on_hand = stock_on_hand + ?, last_updated = CURRENT_TIMESTAMP
                    WHERE store_id = ? AND product_id = ?;
                """, (quantity, store_id, product_id))

                # 3. Log Audit Ledger Entry in stock_movements (positive quantity!)
                movement_notes = f"Restock #{new_restock_id}" + (f" - {notes}" if notes else "")
                cur.execute("""
                    INSERT INTO stock_movements (product_id, store_id, movement_type, quantity, reference_id, movement_date, notes)
                    VALUES (?, ?, 'RESTOCK', ?, ?, CURRENT_TIMESTAMP, ?);
                """, (product_id, store_id, quantity, new_restock_id, movement_notes))

                conn.commit()

                new_stock = current_stock + quantity
                flash(
                    f"Restock #{new_restock_id} recorded successfully! Replenished +{quantity} units of '{product['product_name']}' at {store['store_name']}. New Stock: {new_stock} units (Total Cost: ${total_cost:,.2f}).",
                    "success"
                )
                return redirect(url_for("restock_detail", restock_id=new_restock_id))

            except Exception as e:
                conn.rollback()
                flash(f"Restock transaction failed: {str(e)}", "danger")
                return render_template(
                    "add_restock.html",
                    active_products=active_products,
                    active_stores=active_stores,
                    today_str=today_str,
                    selected_product_id=prod_id_str,
                    selected_store_id=store_id_str,
                    quantity=qty_str,
                    cost_per_unit=cost_str,
                    restock_date=restock_date,
                    notes=notes
                )

        preselected_prod = request.args.get("product_id", "").strip()
        preselected_store = request.args.get("store_id", "").strip()
        return render_template(
            "add_restock.html",
            active_products=active_products,
            active_stores=active_stores,
            today_str=today_str,
            selected_product_id=preselected_prod,
            selected_store_id=preselected_store,
            quantity="20",
            cost_per_unit="",
            restock_date=today_str,
            notes=""
        )

    @app.route("/restock/<int:restock_id>")
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN, auth_service.ROLE_MANAGER)
    def restock_detail(restock_id):
        """View individual restock transaction details, before/after stock levels, and audit trail."""
        restock_rec = db.query_db("""
            SELECT 
                r.restock_id,
                r.restock_date,
                r.quantity,
                r.cost_per_unit,
                ROUND(r.quantity * r.cost_per_unit, 2) AS total_cost,
                r.notes,
                r.created_at,
                p.product_id,
                p.product_name,
                p.category,
                p.cost_price AS catalog_cost,
                p.selling_price,
                st.store_id,
                st.store_name,
                st.city,
                st.location
            FROM restocks r
            JOIN products p ON r.product_id = p.product_id
            JOIN stores st ON r.store_id = st.store_id
            WHERE r.restock_id = ?;
        """, (restock_id,), one=True)

        if not restock_rec:
            abort(404)

        inv = db.query_db("""
            SELECT stock_on_hand, reorder_level, last_updated
            FROM inventory
            WHERE store_id = ? AND product_id = ?;
        """, (restock_rec["store_id"], restock_rec["product_id"]), one=True)

        movement = db.query_db("""
            SELECT movement_id, movement_type, quantity, movement_date, notes
            FROM stock_movements
            WHERE reference_id = ? AND movement_type = 'RESTOCK';
        """, (restock_id,), one=True)

        current_stock = inv["stock_on_hand"] if inv else 0
        stock_added = restock_rec["quantity"]
        # Stock before this restock (approximate if subsequent movements occurred)
        stock_before = max(0, current_stock - stock_added)

        return render_template(
            "restock_detail.html",
            restock=restock_rec,
            inv=inv,
            movement=movement,
            stock_before=stock_before,
            stock_added=stock_added,
            stock_after=current_stock
        )

    # ==========================================================
    # ROUTES - ANALYTICS & PRODUCT MOVEMENT
    # ==========================================================

    @app.route("/analytics")
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN, auth_service.ROLE_MANAGER, auth_service.ROLE_ANALYST)
    def analytics():
        """
        Product Movement Analytics & Sales Velocity view.
        Calculates empirical sales velocity across all products for the selected period,
        assigns percentile-based movement classification (Fast, Normal, Slow),
        and breaks down performance by category and store.
        """
        preset = request.args.get("preset", "full").strip().lower()
        start_date = request.args.get("start_date", "").strip()
        end_date = request.args.get("end_date", "").strip()
        movement_filter = request.args.get("movement", "all").strip().lower()
        category_filter = request.args.get("category", "all").strip()
        sort_by = request.args.get("sort", "velocity").strip().lower()
        sort_dir = request.args.get("order", "desc").strip().lower()

        bounds = analytics_service.get_analysis_date_bounds()

        # Query and classify products for the selected period
        data = analytics_service.get_product_velocity(
            start_date=start_date if start_date else None,
            end_date=end_date if end_date else None,
            preset=preset,
            movement_filter=movement_filter,
            category_filter=category_filter,
            sort_by=sort_by,
            sort_dir=sort_dir
        )

        # Also get unfiltered product list for top fast/slow highlights and category breakdown
        unfiltered_data = analytics_service.get_product_velocity(
            start_date=data["start_date"],
            end_date=data["end_date"],
            preset="custom",
            movement_filter="all",
            category_filter="all",
            sort_by="velocity",
            sort_dir="desc"
        )

        all_products = unfiltered_data["products"]
        fast_products = [p for p in all_products if p["movement_status"] == "FAST MOVING"]
        
        # Slow products sorted by ascending velocity
        slow_products = [p for p in all_products if p["movement_status"] == "SLOW MOVING"]
        slow_products.sort(key=lambda x: (x["sales_velocity"], x["total_units_sold"], x["product_id"]))

        # Category sales & velocity aggregation
        category_summary = analytics_service.get_category_analysis(all_products)

        # Store sales performance foundation (top 15 stores)
        store_summary = analytics_service.get_store_sales_summary(data["start_date"], data["end_date"], limit=15)

        return render_template(
            "analytics.html",
            bounds=bounds,
            start_date=data["start_date"],
            end_date=data["end_date"],
            num_days=data["num_days"],
            active_preset=data["active_preset"],
            summary=data["summary"],
            products=data["products"],
            fast_products=fast_products,
            slow_products=slow_products,
            category_summary=category_summary,
            store_summary=store_summary,
            selected_movement=movement_filter,
            selected_category=category_filter,
            sort_by=sort_by,
            sort_dir=sort_dir
        )

    # ==========================================================
    # ROUTES - RULE-BASED INVENTORY RECOMMENDATIONS
    # ==========================================================

    @app.route("/recommendations")
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN, auth_service.ROLE_MANAGER, auth_service.ROLE_ANALYST)
    def recommendations():
        """
        Rule-Based Inventory Recommendations page.
        Generates explainable decision-support signals by evaluating sales velocity,
        stock on hand, reorder thresholds, and approximate stock coverage.
        """
        preset = request.args.get("preset", "full").strip().lower()
        start_date = request.args.get("start_date", "").strip() or None
        end_date = request.args.get("end_date", "").strip() or None
        recommendation_filter = request.args.get("recommendation", "all").strip()
        priority_filter = request.args.get("priority", "all").strip().upper()
        movement_filter = request.args.get("movement", "all").strip().lower()
        category_filter = request.args.get("category", "all").strip()
        sort_by = request.args.get("sort", "priority").strip().lower()
        sort_dir = request.args.get("order", "asc").strip().lower()

        data = recommendation_service.get_product_recommendations(
            start_date=start_date,
            end_date=end_date,
            preset=preset,
            recommendation_filter=recommendation_filter,
            priority_filter=priority_filter,
            movement_filter=movement_filter,
            category_filter=category_filter,
            sort_by=sort_by,
            sort_dir=sort_dir
        )

        cat_rows = db.query_db("SELECT DISTINCT category FROM products ORDER BY category ASC;")
        categories = [r["category"] for r in cat_rows]

        return render_template(
            "recommendations.html",
            start_date=data["start_date"],
            end_date=data["end_date"],
            num_days=data["num_days"],
            active_preset=data["active_preset"],
            summary=data["summary"],
            recommendations=data["recommendations"],
            total_count=data["total_count"],
            categories=categories,
            selected_recommendation=recommendation_filter,
            selected_priority=priority_filter,
            selected_movement=movement_filter,
            selected_category=category_filter,
            sort_by=sort_by,
            sort_dir=sort_dir
        )

    # ==========================================================
    # ROUTES - PHASE 12: ANALYTICAL REPORTS & POWER BI EXPORTS
    # ==========================================================

    @app.route("/reports")
    @auth_service.login_required
    @auth_service.role_required(auth_service.ROLE_ADMIN, auth_service.ROLE_MANAGER, auth_service.ROLE_ANALYST)
    def reports():
        """
        Analytical Reports and Power BI Export Center.
        Provides preview tables and CSV download actions across 6 analytical datasets.
        """
        active_tab = request.args.get("tab", "sales").strip().lower()

        # Preview datasets (efficiently sliced where appropriate)
        sales_daily_all = report_service.get_sales_daily_report()
        sales_daily_preview = sales_daily_all[:20]

        category_sales = report_service.get_sales_category_report()

        recommendations = report_service.get_recommendation_report()
        product_movement = [
            {
                "product_id": r["product_id"],
                "product_name": r["product_name"],
                "category": r["category"],
                "units_sold": r.get("units_sold", 0),
                "transactions": r.get("transactions", 0),
                "sales_velocity": r["sales_velocity"],
                "movement_status": r["movement_status"],
                "current_stock": r["current_stock"],
                "reorder_level": r["reorder_level"],
                "stock_coverage_days": r["stock_coverage_days"]
            }
            for r in recommendations
        ]

        # Summary KPI cards across the analytical scope (reuses precomputed daily sales & recommendations)
        summary_kpis = report_service.get_report_summary_kpis(
            sales_daily=sales_daily_all,
            recommendations=recommendations
        )

        inv_all = report_service.get_inventory_snapshot_report()
        inventory_preview = inv_all[:50]

        store_sales = report_service.get_store_sales_report()

        return render_template(
            "reports.html",
            active_tab=active_tab,
            summary_kpis=summary_kpis,
            sales_daily_preview=sales_daily_preview,
            sales_daily_total_count=len(sales_daily_all),
            category_sales=category_sales,
            product_movement=product_movement,
            inventory_preview=inventory_preview,
            inventory_total_count=len(inv_all),
            store_sales=store_sales,
            recommendations=recommendations
        )

    @app.route("/reports/export/sales-daily")
    @app.route("/reports/export/sales")
    @auth_service.login_required
    def export_sales_daily():
        """CSV download for daily sales summary (sales_daily.csv)."""
        rows = report_service.get_sales_daily_report()
        fields = ["sale_date", "units_sold", "transaction_count", "calculated_revenue"]
        csv_str = report_service.format_csv(rows, fields)
        return Response(
            csv_str,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=sales_daily.csv"}
        )

    @app.route("/reports/export/sales-category")
    @app.route("/reports/export/category-sales")
    @auth_service.login_required
    def export_sales_category():
        """CSV download for category sales summary (sales_category.csv)."""
        rows = report_service.get_sales_category_report()
        fields = ["category", "units_sold", "transaction_count", "calculated_revenue", "average_units_per_transaction"]
        csv_str = report_service.format_csv(rows, fields)
        return Response(
            csv_str,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=sales_category.csv"}
        )

    @app.route("/reports/export/product-movement")
    @auth_service.login_required
    def export_product_movement():
        """CSV download for product movement classification (product_movement.csv)."""
        rows = report_service.get_product_movement_report()
        fields = [
            "product_id", "product_name", "category", "units_sold", "transactions",
            "sales_velocity", "movement_status", "current_stock", "reorder_level", "stock_coverage_days"
        ]
        csv_str = report_service.format_csv(rows, fields)
        return Response(
            csv_str,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=product_movement.csv"}
        )

    @app.route("/reports/export/inventory-snapshot")
    @app.route("/reports/export/inventory")
    @auth_service.login_required
    def export_inventory_snapshot():
        """CSV download for store inventory snapshot (inventory_snapshot.csv)."""
        rows = report_service.get_inventory_snapshot_report()
        fields = [
            "inventory_id", "store_id", "store_name", "city", "product_id", "product_name",
            "category", "stock_on_hand", "reorder_level", "stock_status", "inventory_value"
        ]
        csv_str = report_service.format_csv(rows, fields)
        return Response(
            csv_str,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=inventory_snapshot.csv"}
        )

    @app.route("/reports/export/store-sales")
    @auth_service.login_required
    def export_store_sales():
        """CSV download for store sales performance (store_sales.csv)."""
        rows = report_service.get_store_sales_report()
        fields = ["store_id", "store_name", "city", "units_sold", "transaction_count", "calculated_revenue"]
        csv_str = report_service.format_csv(rows, fields)
        return Response(
            csv_str,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=store_sales.csv"}
        )

    @app.route("/reports/export/recommendations")
    @auth_service.login_required
    def export_recommendations():
        """CSV download for inventory recommendations (recommendations.csv)."""
        rows = report_service.get_recommendation_report()
        fields = [
            "product_id", "product_name", "category", "movement_status", "current_stock",
            "reorder_level", "sales_velocity", "stock_coverage_days", "recommendation", "reason", "priority"
        ]
        csv_str = report_service.format_csv(rows, fields)
        return Response(
            csv_str,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=recommendations.csv"}
        )

    @app.route("/reports/export/all")
    @auth_service.login_required
    def export_all_powerbi_zip():
        """Creates a ZIP archive containing all 6 normalized CSVs + README.md for 1-click Power BI import."""
        import zipfile
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. Sales Daily
            s_rows = report_service.get_sales_daily_report()
            zf.writestr("sales_daily.csv", report_service.format_csv(s_rows, ["sale_date", "units_sold", "transaction_count", "calculated_revenue"]))
            # 2. Sales Category
            c_rows = report_service.get_sales_category_report()
            zf.writestr("sales_category.csv", report_service.format_csv(c_rows, ["category", "units_sold", "transaction_count", "calculated_revenue", "average_units_per_transaction"]))
            # 3. Product Movement
            m_rows = report_service.get_product_movement_report()
            zf.writestr("product_movement.csv", report_service.format_csv(m_rows, ["product_id", "product_name", "category", "units_sold", "transactions", "sales_velocity", "movement_status", "current_stock", "reorder_level", "stock_coverage_days"]))
            # 4. Inventory Snapshot
            i_rows = report_service.get_inventory_snapshot_report()
            zf.writestr("inventory_snapshot.csv", report_service.format_csv(i_rows, ["inventory_id", "store_id", "store_name", "city", "product_id", "product_name", "category", "stock_on_hand", "reorder_level", "stock_status", "inventory_value"]))
            # 5. Store Sales
            st_rows = report_service.get_store_sales_report()
            zf.writestr("store_sales.csv", report_service.format_csv(st_rows, ["store_id", "store_name", "city", "units_sold", "transaction_count", "calculated_revenue"]))
            # 6. Recommendations
            r_rows = report_service.get_recommendation_report()
            zf.writestr("recommendations.csv", report_service.format_csv(r_rows, ["product_id", "product_name", "category", "movement_status", "current_stock", "reorder_level", "sales_velocity", "stock_coverage_days", "recommendation", "reason", "priority"]))
            # 7. Metadata README
            readme_path = Path(__file__).resolve().parent / "exports" / "powerbi" / "README.md"
            if readme_path.exists():
                zf.writestr("README.md", readme_path.read_text(encoding="utf-8"))

        memory_file.seek(0)
        return Response(
            memory_file.getvalue(),
            mimetype="application/zip",
            headers={"Content-Disposition": "attachment; filename=powerbi_datasets.zip"}
        )

    # ==========================================================
    # ERROR HANDLERS (401, 403, 404, 500, CSRFError)
    # ==========================================================

    @app.errorhandler(401)
    def unauthorized(e):
        if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
            return jsonify({"error": "Unauthorized", "message": "Authentication required."}), 401
        return render_template("errors/401.html"), 401

    @app.errorhandler(403)
    def forbidden(e):
        if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
            return jsonify({"error": "Forbidden", "message": "You do not have permission to access this resource."}), 403
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(e):
        if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
            return jsonify({"error": "Not Found", "message": "The requested resource was not found."}), 404
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
            return jsonify({"error": "Internal Server Error", "message": "An unexpected error occurred."}), 500
        return render_template("errors/500.html"), 500

    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        if request.path.startswith("/api/") or request.headers.get("Accept") == "application/json":
            return jsonify({"error": "Bad Request", "message": "CSRF token missing or invalid."}), 400
        flash("Your security token has expired or is invalid. Please refresh and try again.", "danger")
        return render_template("errors/401.html", csrf_error=True), 400


    return app

app = create_app()

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("Starting Smart Inventory & Sales Analysis System")
    print("Dashboard URL: http://127.0.0.1:5000")
    print("=" * 60 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=True)
