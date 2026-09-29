# Smart Inventory & Sales Analysis System
### Enterprise Retail Decision-Support & Supply Chain Analytics Engine

[![Python 3.10+](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Flask 3.0+](https://img.shields.io/badge/Flask-3.0+-000000?style=flat&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/Database-SQLite_WAL-003B57?style=flat&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Chart.js](https://img.shields.io/badge/Visualizations-Chart.js_4.4-FF6384?style=flat&logo=chartdotjs&logoColor=white)](https://chartjs.org)
[![Power BI](https://img.shields.io/badge/BI_Modeling-Power_BI_PBIP-F2C811?style=flat&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com)
[![Test Suite](https://img.shields.io/badge/Automated_Tests-12%2F12_Suites_Passed-10B981?style=flat)](scripts/run_all_regressions.py)
[![Security Auth](https://img.shields.io/badge/Security_Auth-25%2F25_Passed-blue?style=flat)](scripts/test_auth.py)

---

## 1. Project Overview

The **Smart Inventory & Sales Analysis System** is an end-to-end, production-grade retail supply chain management and business intelligence platform. Built on historical transaction data from **Maven Toys** (a regional toy retail chain with 50 store locations across Mexico), the system bridges transactional inventory operations (POS sales checkout, inbound restock replenishment, and an immutable double-entry stock movement ledger) with empirical sales velocity analytics, rule-based recommendation signals, and a standardized Power BI Star-Schema data model.

---

## 2. Business Problem

Retail chains managing dozens of distributed stores across multiple merchandise departments frequently suffer from two opposing operational crises:
1. **Stockouts on High-Velocity Products:** Popular, fast-selling SKUs run out of stock without early warning, leading to missed revenue and lost customer goodwill.
2. **Capital Trapped in Overstocked Slow-Movers:** Low-velocity items accumulate excess physical inventory across store branches, tying up working capital and increasing storage costs.
3. **Disconnected Reporting Silos:** Operations teams manage daily inventory in transactional systems without access to analytical velocity metrics, while executive BI dashboards display stale numbers disconnected from transactional stock movements.

This system resolves these challenges by integrating **real-time transactional inventory tracking**, **empirical velocity calculation (units/day)**, **automated inventory reorder thresholds**, and **explainable decision-support recommendations** backed by high-performance SQL indexes and a Power BI Star Schema.

---

## 3. Key Capabilities

- **Atomic Inventory Control:** ACID-compliant sales checkout and inbound restock transactions enforced by SQLite foreign keys and transaction rollbacks.
- **Double-Entry Stock Audit Trail:** Every stock decrement (`SALE`) or increment (`RESTOCK`) writes an immutable record to `stock_movements`.
- **Empirical Sales Velocity Engine:** Dynamic calculation of product velocity (`units sold / calendar trading days`) over custom timeframes or the full 638-day historical baseline.
- **Data-Driven Percentile Classification:** Automatic categorization of catalog items into `FAST MOVING` (Top 25%), `NORMAL` (Middle 50%), and `SLOW MOVING` (Bottom 25%).
- **Rule-Based Decision-Support Engine:** 7 explainable business logic rules evaluating current network stock against reorder thresholds and daily velocity to generate prioritized replenishment actions (`PRIORITIZE REPLENISHMENT`, `REPLENISH SOON`, `MONITOR STOCK`, `REVIEW INVENTORY LEVEL`, `MAINTAIN CURRENT LEVEL`, `MONITOR`).
- **High-Performance Executive Web Dashboard:** 9 interactive Chart.js visualizations driven by SQL-aggregated endpoints, eliminating heavy client-side row loading across 829k sales records.
- **Reports & Normalized Power BI Pipeline:** Standardized automated exporter generating 9 UTF-8 CSV datasets and a portable Star Schema Power BI project (`.pbip`) with 23 pre-built DAX measures.

---

## 4. Technology Stack

- **Backend Framework:** Python 3.10+, Flask 3.0+ (Application Factory pattern, Blueprints, modular service architecture)
- **Database Engine:** SQLite 3 with Write-Ahead Logging (`PRAGMA journal_mode = WAL`), 30-second busy timeout, and composite covering B-tree indexes
- **Frontend / UI:** Semantic HTML5, Vanilla CSS Design System with CSS variables, responsive mobile sidebar drawer, Inter typography, Chart.js 4.4.0 (locally vendored)
- **Data Modeling & Analytics:** Microsoft Power BI (`.pbip` project, TMSL `model.bim`, DAX measures library, Power Query M code)
- **Testing & Verification:** Comprehensive Python regression test suites (147 verification assertions across 8 test suites)

---

## 5. Architecture & End-to-End Data Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DATA INGESTION & STORAGE                        │
├────────────────────────────────────────────────────────────────────────┤
│  Raw CSV Sources          ETL Pipeline                SQLite Database  │
│  (sales, products,   ──►  (scripts/init_db.py)  ──►   (inventory.db)   │
│   stores, inventory)       Cleaning & Indexing        WAL Concurrency  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       FLASK APPLICATION & SERVICES                     │
├────────────────────────────────────────────────────────────────────────┤
│  Operational Layer:          Analytics Layer:        Reporting Layer:  │
│  * POS Sales Checkout        * Sales Velocity        * Table Previews  │
│  * Inbound Restock Flow      * Movement Percentiles  * Export Pipeline │
│  * Atomic Stock Movements    * Rule Recommendation   * ZIP Downloads   │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        CONSUMPTION & REPORTING                         │
├────────────────────────────────────────────────────────────────────────┤
│  Web Application (Port 5000)             Power BI Desktop Report       │
│  * Executive Dashboard (9 Charts)        * Star Schema Data Model      │
│  * Inventory Management Grid             * 23 DAX Measures             │
│  * Velocity & Recommendation Tables      * 5 Analytical Pages          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Dataset Description

The system processes real-world retail store data from Maven Toys:
- **`sales.csv` (21.78 MB, 829,262 rows):** Individual sales checkout events covering **2017-01-01** to **2018-09-30** (638 active trading days). Cumulative volume: **1,090,565 physical units sold**.
- **`products.csv` (1.57 KB, 35 rows):** Catalog merchandise across 5 categories (*Art & Crafts, Electronics, Games, Sports & Outdoors, Toys*) with product cost and retail price.
- **`stores.csv` (2.99 KB, 50 rows):** Physical store locations across 29 Mexican cities, store opening dates (ranging from 1992 to 2014), and location classifications (*Airport, Commercial, Downtown, Residential*).
- **`inventory.csv` (14.67 KB, 1,516 rows raw / 1,750 normalized grid):** Store-SKU current inventory levels.

---

## 7. Database Schema Overview

```mermaid
erDiagram
    products ||--o{ inventory : "1:N"
    products ||--o{ sales : "1:N"
    products ||--o{ restocks : "1:N"
    products ||--o{ stock_movements : "1:N"
    stores ||--o{ inventory : "1:N"
    stores ||--o{ sales : "1:N"
    stores ||--o{ restocks : "1:N"
    stores ||--o{ stock_movements : "1:N"

    products {
        int product_id PK
        string product_name
        string category
        decimal cost_price
        decimal selling_price
        int active
    }

    stores {
        int store_id PK
        string store_name
        string city
        string location
        date open_date
        int active
    }

    inventory {
        int inventory_id PK
        int store_id FK
        int product_id FK
        int stock_on_hand
        int reorder_level
        string stock_status
    }

    sales {
        int sale_id PK
        date sale_date
        int store_id FK
        int product_id FK
        int quantity
        decimal total_amount
    }

    restocks {
        int restock_id PK
        int product_id FK
        int store_id FK
        int quantity
        decimal cost_per_unit
        date restock_date
        string notes
    }

    stock_movements {
        int movement_id PK
        int product_id FK
        int store_id FK
        string movement_type
        int quantity
        int reference_id
        timestamp created_at
    }
```

### High-Performance Composite Indexes
To ensure sub-second query performance over 829,262 sales rows:
- `idx_sales_store_perf` ON `sales(store_id, quantity, total_amount)` (Store-level sales aggregations: 40x speedup from 17.3s &rarr; 0.43s)
- `idx_sales_date_perf` ON `sales(sale_date, quantity, total_amount)` (Daily sales timeline aggregation: 1.5s &rarr; 0.51s)
- `idx_sales_product_perf` ON `sales(product_id, quantity, total_amount)` (Product velocity aggregations: 0.24s)
- `idx_sales_date_prod_agg` ON `sales(sale_date, product_id, quantity, total_amount)` (CTE date-filtered velocity queries: 2.1s)
- `idx_inventory_store_prod` ON `inventory(store_id, product_id)` (Unique composite constraint and instant store-SKU lookups)

---

## 8. Cleaning & ETL Process

The ETL pipeline ([scripts/init_db.py](scripts/init_db.py) and [scripts/data_cleaning.py](scripts/data_cleaning.py)) sanitizes raw CSV files without mutating source data:
1. Strips non-numeric characters, currency symbols (`$`), and commas from prices and IDs.
2. Formats all calendar dates to standard ISO-8601 (`YYYY-MM-DD`).
3. Fills missing store-product combinations with 0 on-hand stock and default reorder levels, normalizing the inventory grid to exactly **1,750 store-SKU pairs** (50 stores &times; 35 products).
4. Generates initial inventory baseline stock movements.

---

## 9. Inventory Logic & Dynamic Stock Status

Each store-SKU dynamically evaluates its stock status based on physical stock on hand and its configured reorder threshold:
- **`OUT OF STOCK`:** `stock_on_hand == 0` (234 store-SKUs / 13.4% of network).
- **`LOW STOCK`:** `0 < stock_on_hand < reorder_level` (526 store-SKUs / 30.1% of network).
- **`NORMAL`:** `stock_on_hand >= reorder_level` (990 store-SKUs / 56.6% of network).

---

## 10. Sales Workflow (Atomic Decrement)

1. User selects Store and Product on `/sales/add`.
2. Asynchronous API (`/api/inventory/lookup`) fetches live stock on hand.
3. Form validates quantity: must be positive integer and cannot exceed `stock_on_hand`.
4. Transaction executes atomically inside a SQLite transaction:
   - Inserts record into `sales`.
   - Decrements `inventory.stock_on_hand` by sale quantity.
   - Logs negative quantity into `stock_movements` with `movement_type = 'SALE'`.
5. If any step fails, the entire transaction rolls back cleanly.

---

## 11. Restock Workflow (Atomic Increment)

1. User selects Store, Product, Quantity, and Cost per Unit on `/restock/add`.
2. Form validates quantity > 0 and cost per unit >= 0.
3. Transaction executes atomically:
   - Inserts record into `restocks`.
   - Increments `inventory.stock_on_hand` by restock quantity.
   - Logs positive quantity into `stock_movements` with `movement_type = 'RESTOCK'`.
4. Updates visible inventory and detail views immediately.

---

## 12. Stock Movement Audit Trail

Every operational transaction modifies the inventory balance exclusively through logged stock movements:
- `INITIAL`: Opening baseline stock initialization.
- `SALE`: Outbound negative unit movement linked to `sale_id`.
- `RESTOCK`: Inbound positive unit movement linked to `restock_id`.

---

## 13. Sales Velocity Methodology

Sales velocity represents the rate at which an item sells per calendar trading day:

$$\text{Sales Velocity} = \frac{\text{Total Units Sold in Period}}{\text{Number of Calendar Trading Days in Period}}$$

For the full historical observation baseline (`2017-01-01` to `2018-09-30`):
- Total Calendar Days: **638 days**
- Total Units Sold: **1,090,565 units**
- Overall Catalog Average Velocity: **48.86 units/day**

---

## 14. Fast / Normal / Slow Classification Methodology

Rather than arbitrary hardcoded cutoffs, movement tiers are derived empirically from the dataset's percentile distribution:
- **Top 25% Velocity Percentile ($\ge 66.43\text{ units/day}$):** Classified as **`FAST MOVING`** (**9 products**).
- **Middle 50% Velocity Percentile ($10.36\text{ to }66.42\text{ units/day}$):** Classified as **`NORMAL`** (**17 products**).
- **Bottom 25% Velocity Percentile ($\le 10.36\text{ units/day}$):** Classified as **`SLOW MOVING`** (**9 products**).

---

## 15. Recommendation Engine Rules

The recommendation engine ([services/recommendation_service.py](services/recommendation_service.py)) evaluates stock coverage cushion:

$$\text{Stock Coverage Days} = \frac{\text{Current Stock on Hand}}{\text{Sales Velocity (units/day)}}$$

7 deterministic rules prioritize replenishment:
1. **Rule B (Priority HIGH):** `FAST MOVING` + `Current Stock == 0` &rarr; **`PRIORITIZE REPLENISHMENT`**
2. **Rule A (Priority HIGH):** `FAST MOVING` + `Current Stock < Reorder Level` &rarr; **`REPLENISH SOON`**
3. **Rule C (Priority MEDIUM):** `FAST MOVING` + `Stock Coverage < 14 Days` &rarr; **`MONITOR STOCK`**
4. **Rule D (Priority MEDIUM):** `SLOW MOVING` + `Current Stock >= Reorder Level` &rarr; **`REVIEW INVENTORY LEVEL`**
5. **Rule E (Priority MEDIUM):** `SLOW MOVING` + `Current Stock < Reorder Level` &rarr; **`REPLENISH OR REVIEW`**
6. **Rule F (Priority LOW):** `NORMAL` + `Current Stock >= Reorder Level` &rarr; **`MAINTAIN CURRENT LEVEL`**
7. **Rule G (Priority NONE):** Fallback healthy / balanced inventory &rarr; **`MONITOR`**

Chain-wide aggregate baseline: **7 products require operational attention** (7 Medium priority, 0 High priority at aggregate chain level).

---

## 16. Dashboard & Analytics

The executive dashboard (`/dashboard`) provides 9 responsive visualizations:
1. **Sales Volume Trend:** Daily units sold timeline with moving average.
2. **Calculated Revenue Trend:** Financial volume timeline.
3. **Category Sales Breakdown:** Donut chart of volume by merchandise department.
4. **Top 10 Selling Products:** Horizontal bar chart of catalog volume leaders.
5. **Network Inventory Health:** Donut chart of Normal, Low Stock, and Out of Stock store-SKUs.
6. **On-Hand Units by Category:** Physical stock volume distribution.
7. **Store Sales Performance:** Top 5, Top 10, or All 50 retail branches.
8. **Movement Tier Distribution:** Fast, Normal, and Slow distribution.
9. **Decision Support Alerts:** Inventory Attention summary cards.

---

## 17. Power BI Integration

The system includes a dedicated Power BI Project under [powerbi/](powerbi):
- **Project Structure:** `SmartInventory_Analytics.pbip` with dataset definition and TMSL `model.bim`.
- **Configurable `SourceFolder` Parameter:** Relative path default (`..\exports\powerbi\`) enables portable opening from any machine directory.
- **Strict Star Schema:** Dimensions filter facts exclusively in a single direction (`oneDirection`). Zero bidirectional relationships.
- **23 Pre-Built DAX Measures:** Formatted in [exports/powerbi/dax_measures.dax](exports/powerbi/dax_measures.dax).

---

## 18. Calculated Revenue Definition

> [!IMPORTANT]
> Historical sales checkout logs from Maven Toys recorded unit quantities sold without itemized register receipt checkout prices. Revenue figures across the entire project represent **Calculated Revenue** evaluated at catalog retail selling price:
>
> $$\text{Calculated Revenue} = \sum (\text{Quantity Sold} \times \text{Catalog Retail Selling Price})$$
>
> These are decision-support estimates and should not be presented as statutory financial accounting receipts.

---

## 19. Calculated Inventory Valuation Definition

> [!IMPORTANT]
> Inventory valuation represents **Calculated Valuation** evaluated at retail catalog selling price:
>
> $$\text{Calculated Inventory Value} = \sum (\text{Stock on Hand} \times \text{Catalog Retail Selling Price})$$

---

## 20. Current Inventory Snapshot Limitation

> [!IMPORTANT]
> Inventory balances (`stock_on_hand`, `stock_status`, `inventory_value`) represent the **live operational snapshot** of the retail chain. They do **not** represent historical daily store balances across 2017–2018. When filtering sales by date, inventory stock figures reflect the current state.

---

## 21. How to Install Dependencies

1. Clone repository:
   ```bash
   git clone https://github.com/your-username/inventory-analysis.git
   cd inventory-analysis
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On Linux/macOS:
   source venv/bin/activate
   ```
3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

---

## 22. How to Initialize / Import the Database

The repository ships with the validated baseline database at `database/inventory.db`. To re-import from raw source CSVs:
```bash
python scripts/init_db.py
```
This sanitizes the raw data, creates all tables, builds composite covering indexes, and populates the database to the verified baseline.

---

## 23. How to Start Flask

```bash
python app.py
```
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## 24. Enterprise Authentication & Role-Based Access Control (RBAC)

The application features a production-hardened, authoritative server-side authentication and Role-Based Access Control (RBAC) architecture designed for multi-tier retail operations.

### Final User Roles & Access Matrix

The system implements exactly four operational roles:

| Role | Public Signup? | Permitted Modules & Operations | Restricted / Barred Operations |
| :--- | :---: | :--- | :--- |
| **System Administrator** | ❌ Excluded | Full operational, analytical, reporting, catalog, inventory, and governance access (`/admin/users`). Can view all accounts, modify user roles, and toggle account activation status. | Universal access across all application boundaries. |
| **Inventory Manager** | ✅ Selectable | Dashboard (full view), Products (add/edit/deactivate), Inventory, Sales POS, Restocking (`/restock/add`), Velocity Analytics, Inventory Recommendations, Reports, Power BI data exports, and My Profile. | Barred from User & Role Governance (`/admin/users`). Direct access returns `HTTP 403 Forbidden`. |
| **Data Analyst** | ✅ Selectable | Dashboard (analytical workspace), Inventory (read-only), Sales (read-only), Velocity Analytics (`/analytics`), Recommendations (`/recommendations`), Reports (`/reports` & `/powerbi`), Power BI exports, and My Profile. | Barred from operational stock-altering actions (`/products/add`, `/restock/add`) and User Governance (`/admin/users`). Direct access returns `HTTP 403 Forbidden`. |
| **Store Associate** | ✅ Selectable | Dashboard (POS terminal & live stock lookup), Point-of-Sale Transactions (`/sales/add`), Physical Stock Lookup (`/inventory`), and My Profile. | Barred from Product Catalog administration, Restocking, Analytics, Recommendations, Reports/Power BI, and User Governance. Direct access returns `HTTP 403 Forbidden`. |

### Public Sign-Up & Configurable Role Selection (`/signup`)
- **Publicly Selectable Roles:** New visitors creating an account on `/signup` can select from:
  - `Store Associate`
  - `Data Analyst`
  - `Inventory Manager`
- **System Administrator is Strictly Excluded:** The administrative governance role is never selectable in the public sign-up interface. Server-side validation rejects any attempt to register an administrator account with `HTTP 400 Bad Request`.
- **Configurability:** Public role selection is controlled by `ALLOW_PUBLIC_ROLE_SELECTION` (default: `True` in `config.py`). When set to `False`, all new registrations default strictly to least-privileged `Store Associate`.
- **Immediate Role Activation:** For college/portfolio demonstration, the selected registration role is stored in SQLite and immediately controls application authorization upon automatic login.

### Email Validation & Normalization
- **Authoritative Server-Side Validation:** Enforces strict RFC-compliant email structure (`local_part@domain.tld`):
  - Exactly one `@` symbol
  - Non-empty username before `@` without invalid special characters
  - Non-empty domain after `@` with valid dot segments and top-level domain (`len(tld) >= 2`)
  - No whitespace characters
- **Client-Side Immediate Feedback:** Real-time JavaScript validation in `signup.html` and `login.html` provides instant visual confirmation and prevents erroneous submissions.
- **Rejected Malformed Patterns:** `ankitgmail.com` (missing `@`), `ankit@` (missing domain), `@gmail.com` (missing local part), `ankit @gmail.com` (whitespace), `ankit@gmail` (missing TLD), `ankit.com` (missing `@`).
- **Accepted Patterns:** `ankit@gmail.com`, `user@example.com`.
- **Lowercase Normalization:** All emails are converted to lowercase before database query, uniqueness check, and storage. `ANKIT@GMAIL.COM` and `ankit@gmail.com` map to the identical account. Duplicate emails are cleanly rejected.

### Password Security & Policies
- **Scrypt Password Hashing:** Passwords hashed with Werkzeug `scrypt:32768:8:1`. Plaintext passwords are never stored, transmitted in logs, or placed in session cookies.
- **Complexity Requirements:** Minimum 8 characters, requiring at least one letter and at least one digit or special character.
- **Common Weak Password Blacklist:** Prevents trivial passwords (`password123`, `admin123`, `12345678`, etc.).
- **Confirmation Matching:** Password and Confirm Password must match identically.

### Sign-In Role Verification Consistency Check (`/login`)
- **Required Fields:** Email, Password, and Role selector (`System Administrator`, `Inventory Manager`, `Data Analyst`, `Store Associate`).
- **Security Rule:** Selecting a role on the login form is an **authentication consistency check**—it does NOT grant or elevate privileges.
- **Authoritative Backend Flow:**
  1. Find user by normalized lowercase email.
  2. Verify password cryptographic hash (`check_password_hash`).
  3. Verify account is active (`is_active == 1`).
  4. Verify account is not locked (`locked_until == NULL` or expired).
  5. **Verify selected login role matches the stored role in the database.**
  6. Only establish authenticated session if all checks pass.
- **Generic Error Response:** If the password is correct but the user selects a role that does not match their stored database role, authentication is rejected with:
  > *"Invalid email, password, or role."*
- **Enumeration Defense:** The system never reveals whether email, password, or role was incorrect, mitigating user enumeration attacks.
- *Role selection during login is verified against the role stored for the authenticated account. Selecting a different role does not grant additional permissions.*

### Server-Side Authorization & Direct URL Defense
- Never trusts frontend role data, JavaScript state, cookies, or query parameters.
- Protected routes use `@auth_service.login_required` and `@auth_service.role_required(...)`.
- Direct URL tampering (e.g. Store Associate navigating to `/analytics` or `/restock/add`, Data Analyst navigating to `/products/add`, or Inventory Manager navigating to `/admin/users`) is trapped server-side and returns `HTTP 403 Forbidden` with a branded security page.
- API endpoints (`/api/analytics/*`, `/api/recommendations*`, `/api/dashboard/*`) enforce role requirements and return `HTTP 401 Unauthorized` or `HTTP 403 Forbidden` JSON payloads.

### Role-Aware Dynamic Dashboard (`/dashboard`)
The application features a single, unified `/dashboard` route that renders dynamically based on the authenticated user's role:
- **Inventory Manager:** Complete executive and operational overview with 7 KPI cards (Total Units Sold, Calculated Revenue, Current Inventory, Inventory Value, Low Stock, Out of Stock, Attention Flagged), Manager Quick Actions bar, 9 interactive Chart.js visualizations, replenishment decision support table with Restock buttons, and recent transactions.
- **System Administrator:** All Inventory Manager capabilities plus an Administrator Governance alert banner linking directly to `/admin/users`.
- **Data Analyst:** Analysis-focused workspace highlighting Sales Velocity (units/SKU/day), Movement Distribution (Fast/Normal/Slow percentiles), Recommendation signals, Category revenue mix, trend charts, and read-only Attention Review table without stock-altering controls.
- **Store Associate:** Streamlined operational terminal emphasizing POS checkout ("Record New Sale"), live interactive Stock Availability Lookup widget, operational stock KPI cards (Stock on Hand, Healthy, Low Stock, Out of Stock), and recent sales activity without analytical charts or management clutter.

### User Profiles & Account Management
- **My Profile (`/profile`):** Displays account metadata (Full Name, Email, User ID, Role badge, Account Status, Creation Date, Last Login).
- **Edit Profile (`/profile/edit`):** Users can edit Full Name and Email. Changing Email strictly requires Current Password verification.
- **Immutable Attributes:** User ID, Role, and Account Status cannot be changed by the user; updates are bound to `session["user_id"]` (preventing IDOR).
- **Change Password (`/profile/password`):** Verifies current password, enforces password complexity, generates new scrypt hash, and invalidates active sessions (`session.clear()`).
- **User Governance (`/admin/users`):** Administrator-only portal to view all users, update operational roles, and activate/deactivate accounts.

### Development / Seeded Accounts

Development/demo credentials are configured locally through environment variables and are not stored in committed documentation.

For local demonstration, evaluation, and automated testing, the pre-seeded account emails and their designated role scopes are:

| Role | Account Email | Scope of Access |
| :--- | :--- | :--- |
| **System Administrator** | `admin@inventory.com` | Full access + User & Role Governance (`/admin/users`) |
| **Inventory Manager** | `manager@inventory.com` | Master Catalog, Stock, Restock POS, Analytics & Reports |
| **Data Analyst** | `analyst@inventory.com` | Executive Dashboard, Velocity Analytics, Reports & BI Exports |
| **Store Associate** | `associate@inventory.com` | POS Transactions, Physical Stock Lookup |

> [!NOTE]
> Development/demo credentials are configured locally through environment variables and are not stored in committed documentation. Demo accounts are maintained for local evaluation and automated regression testing. In production deployments, demo accounts must be disabled or secured with strong environment-provided secrets.

---

## 25. How to Run All Tests

To run the complete automated test suite across all 13 development and security phases in one command:
```bash
python scripts/run_all_regressions.py
```

Or execute individual test suites:
```bash
# Core Domain Regressions (Phases 6–12)
python scripts/test_phase6.py
python scripts/test_phase7.py
python scripts/test_phase8.py
python scripts/test_phase9.py
python scripts/test_phase10.py
python scripts/test_phase11.py
python scripts/test_phase12.py

# Power BI Data Model & Measures (Phase 13)
python scripts/validate_phase13_model.py
python scripts/test_phase13.py

# Route Presentation & Business Workflow (Phase 14)
python scripts/test_route_validation.py
python scripts/test_business_workflow.py

# Enterprise Authentication & Security Suite (25 Tests)
python scripts/test_auth.py

# User Profile & Account Management Suite (25 Tests)
python scripts/test_profile.py

# Headless Chrome Browser Lifecycle Validation
python scripts/test_auth_browser_headless.py
python scripts/test_profile_browser_headless.py
```

---

## 26. Expected Baseline Validation Numbers

All analytical calculations, test suites, and Power BI models must reconcile to these exact baseline numbers:

| Metric | Baseline Value | Source Table / Definition |
|:---|:---:|:---|
| **Products Count** | `35` | Master catalog products |
| **Stores Count** | `50` | Active retail branch stores |
| **Store-SKU Inventory Combinations** | `1,750` | 50 stores &times; 35 products |
| **Historical Sales Records** | `829,262` | Checkout transaction rows |
| **Inbound Restocks** | `0` | Clean baseline state |
| **Logged Stock Movements** | `1,516` | Initial opening movements |
| **Total Units Sold** | `1,090,565` | Sum of historical quantities |
| **Total Calculated Revenue** | `$14,444,572.35` | Units &times; selling price |
| **Current Inventory Stock Units** | `29,742` | Physical on-hand stock |
| **Calculated Inventory Valuation** | `$410,240.58` | Stock &times; selling price |
| **Low Stock Store-SKUs** | `526` | 0 < stock < reorder level |
| **Out of Stock Store-SKUs** | `234` | stock == 0 |
| **Normal Stock Store-SKUs** | `990` | stock >= reorder level |
| **Movement Classification (Fast/Normal/Slow)** | `9 / 17 / 9` | Empirical velocity percentiles |
| **Products Requiring Attention** | `7` | High + Medium recommendation priority |

---

## 27. Folder Structure

```text
inventory-analysis/
├── app.py                      # Main Flask application factory & routing
├── config.py                   # Environment configuration & app settings
├── db.py                       # SQLite database connection & teardown hooks
├── requirements.txt            # Python dependencies (Flask, Werkzeug, Flask-WTF)
├── README.md                   # Comprehensive project documentation
├── .gitignore                  # Git commit exclusions
├── database/
│   └── inventory.db            # Production SQLite database (WAL mode)
├── data/
│   └── raw/                    # Immutable raw source CSV files
│       ├── products.csv
│       ├── stores.csv
│       ├── inventory.csv
│       └── sales.csv
├── docs/                       # Technical architecture & verification docs
│   ├── authentication_verification_report.md
│   ├── powerbi_report.md
│   └── final_verification_report.md
├── exports/
│   └── powerbi/                # Normalized Power BI export pipeline
│       ├── sales_daily.csv
│       ├── sales_category.csv
│       ├── product_movement.csv
│       ├── inventory_snapshot.csv
│       ├── store_sales.csv
│       ├── recommendations.csv
│       ├── dim_date.csv
│       ├── dim_products.csv
│       ├── dim_stores.csv
│       ├── dax_measures.dax
│       ├── powerquery_m_code.m
│       └── README.md
├── powerbi/                    # Microsoft Power BI Project (.pbip)
│   ├── SmartInventory_Analytics.pbip
│   ├── SmartInventory_Analytics.Dataset/
│   │   ├── definition.pbidataset
│   │   └── model.bim
│   └── SmartInventory_Analytics.Report/
│       ├── definition.pbir
│       └── report.json
├── services/                   # Modular business logic services
│   ├── auth_service.py         # Authentication, scrypt hashing, RBAC, abuse defense
│   ├── analytics_service.py    # Sales velocity & percentile movement classification
│   ├── recommendation_service.py # Rule-based inventory recommendation engine
│   ├── dashboard_service.py    # SQL aggregations for interactive Chart.js widgets
│   └── report_service.py       # Reporting previews & CSV export pipeline
├── static/
│   ├── css/
│   │   └── style.css           # Core design system styles
│   ├── js/
│   │   ├── main.js             # Navigation & global UI scripts
│   │   └── dashboard.js        # Chart.js asynchronous chart managers
│   └── vendor/
│       └── chart.umd.min.js    # Vendored Chart.js 4.4.0 library
├── templates/                  # Jinja2 presentation templates
│   ├── base.html
│   ├── login.html              # Hardened Sign-In with remember me & eye toggle
│   ├── signup.html             # Safe Sign-Up with strength meter & checklist
│   ├── profile.html            # User Profile & Account Overview
│   ├── edit_profile.html       # Edit Full Name & Work Email
│   ├── change_password.html    # Password update with strength meter
│   ├── dashboard.html
│   ├── products.html
│   ├── add_product.html
│   ├── edit_product.html
│   ├── product_detail.html
│   ├── inventory.html
│   ├── sales.html
│   ├── add_sale.html
│   ├── sale_detail.html
│   ├── restock.html
│   ├── add_restock.html
│   ├── restock_detail.html
│   ├── analytics.html
│   ├── recommendations.html
│   ├── reports.html
│   ├── admin/
│   │   └── users.html          # Administrator User & Role Governance
│   └── errors/
│       ├── 401.html            # Branded Unauthorized Error Page
│       ├── 403.html            # Branded Forbidden Error Page
│       ├── 404.html            # Branded Page Not Found
│       └── 500.html            # Branded Server Error
└── scripts/                    # Test suites & CLI automation utilities
    ├── init_db.py
    ├── data_cleaning.py
    ├── export_reports.py
    ├── build_powerbi_project.py
    ├── test_phase6.py
    ├── test_phase7.py
    ├── test_phase8.py
    ├── test_phase9.py
    ├── test_phase10.py
    ├── test_phase11.py
    ├── test_phase12.py
    ├── validate_phase13_model.py
    ├── test_phase13.py
    ├── test_route_validation.py
    ├── test_business_workflow.py
    ├── test_auth.py            # 25 Enterprise security & RBAC tests
    ├── test_profile.py         # 25 User profile & account management tests
    ├── test_auth_browser_headless.py # Headless Chrome auth renderer
    ├── test_profile_browser_headless.py # Headless Chrome profile renderer
    └── run_all_regressions.py  # Master test runner (13/13 suites)
```

---

## 28. Known Limitations

1. **Headless BI Validation Scope:** Visual rendering inside the Power BI Desktop GUI was not performed because this verification environment runs headlessly via CLI. The project supplies complete data model definitions, Star Schema single-direction relationships, M transformations, 23 DAX measures, and `.pbip` schema files ready for immediate opening in Power BI Desktop.
2. **Current vs. Historical Inventory:** Store inventory stock balances represent the live current operational snapshot. Historical daily stock balances are not reconstructed from sales dates.
3. **Calculated Revenue:** Revenue is estimated using units &times; catalog retail price rather than cashier register receipt pricing.
4. **Session Scope:** Sessions rely on signed HTTPOnly cookies (`SECRET_KEY`). Distributed multi-node scaling would use Redis. MFA/TOTP and email password resets are deferred production opportunities.

---

## 29. Project Status

**AUTHENTICATION UPGRADE & PHASES 1–14 FULLY COMPLETE, HARDENED, AND VERIFIED.**  
All 12 automated test suites (172+ assertions) pass with 100% green status. All data models, web interfaces, authentication controls, and documentation are synchronized with zero regressions.
