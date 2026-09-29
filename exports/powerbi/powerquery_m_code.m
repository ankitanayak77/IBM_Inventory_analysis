// ===============================================================================
// SMART INVENTORY & SALES ANALYSIS SYSTEM - POWER QUERY (M) IMPORT SCRIPT
// ===============================================================================
// Phase 13: Standardized Power Query ETL Definitions
// Instructions:
// 1. In Power BI Desktop, open 'Power Query Editor'.
// 2. Create a Parameter named 'SourceFolder' (Text) pointing to:
//    "..\exports\powerbi\" (or your local exports/powerbi directory path)
// 3. Create a Blank Query for each block below, open 'Advanced Editor', and paste.
// ===============================================================================

// -------------------------------------------------------------------------------
// Parameter: SourceFolder (Configurable & Portable)
// -------------------------------------------------------------------------------
"..\exports\powerbi\" meta [IsParameterQuery=true, Type="Text", IsParameterQueryRequired=true]


// -------------------------------------------------------------------------------
// Query 1: DimDate (638 rows, Grain: 1 row per calendar day)
// -------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "dim_date.csv"), [Delimiter=",", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"date", type date},
        {"year", Int64.Type},
        {"month_number", Int64.Type},
        {"month_name", type text},
        {"quarter", type text},
        {"year_month", type text},
        {"day", Int64.Type},
        {"day_of_week", type text}
    })
in
    TypedTable


// -------------------------------------------------------------------------------
// Query 2: DimProducts (35 rows, Grain: 1 row per catalog product)
// -------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "dim_products.csv"), [Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"product_id", Int64.Type},
        {"product_name", type text},
        {"category", type text},
        {"cost_price", type number},
        {"selling_price", type number}
    })
in
    TypedTable


// -------------------------------------------------------------------------------
// Query 3: DimStores (50 rows, Grain: 1 row per retail store)
// -------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "dim_stores.csv"), [Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"store_id", Int64.Type},
        {"store_name", type text},
        {"city", type text},
        {"location", type text},
        {"open_date", type date}
    })
in
    TypedTable


// -------------------------------------------------------------------------------
// Query 4: FactSalesDaily (638 rows, Grain: 1 row per calendar day)
// -------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "sales_daily.csv"), [Delimiter=",", Columns=4, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"sale_date", type date},
        {"units_sold", Int64.Type},
        {"transaction_count", Int64.Type},
        {"calculated_revenue", type number}
    })
in
    TypedTable


// -------------------------------------------------------------------------------
// Query 5: FactInventorySnapshot (1,750 rows, Grain: 1 row per store-SKU)
// -------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "inventory_snapshot.csv"), [Delimiter=",", Columns=11, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"inventory_id", Int64.Type},
        {"store_id", Int64.Type},
        {"store_name", type text},
        {"city", type text},
        {"product_id", Int64.Type},
        {"product_name", type text},
        {"category", type text},
        {"stock_on_hand", Int64.Type},
        {"reorder_level", Int64.Type},
        {"stock_status", type text},
        {"inventory_value", type number}
    })
in
    TypedTable


// -------------------------------------------------------------------------------
// Query 6: FactStoreSales (50 rows, Grain: 1 row per retail store)
// -------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "store_sales.csv"), [Delimiter=",", Columns=6, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"store_id", Int64.Type},
        {"store_name", type text},
        {"city", type text},
        {"units_sold", Int64.Type},
        {"transaction_count", Int64.Type},
        {"calculated_revenue", type number}
    })
in
    TypedTable


// -------------------------------------------------------------------------------
// Query 7: ProductMovement (35 rows, Grain: 1 row per catalog product)
// -------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "product_movement.csv"), [Delimiter=",", Columns=10, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"product_id", Int64.Type},
        {"product_name", type text},
        {"category", type text},
        {"units_sold", Int64.Type},
        {"transactions", Int64.Type},
        {"sales_velocity", type number},
        {"movement_status", type text},
        {"current_stock", Int64.Type},
        {"reorder_level", Int64.Type},
        {"stock_coverage_days", type number}
    })
in
    TypedTable


// -------------------------------------------------------------------------------
// Query 8: Recommendations (35 rows, Grain: 1 row per catalog product)
// -------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "recommendations.csv"), [Delimiter=",", Columns=11, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"product_id", Int64.Type},
        {"product_name", type text},
        {"category", type text},
        {"movement_status", type text},
        {"current_stock", Int64.Type},
        {"reorder_level", Int64.Type},
        {"sales_velocity", type number},
        {"stock_coverage_days", type number},
        {"recommendation", type text},
        {"reason", type text},
        {"priority", type text}
    })
in
    TypedTable


// -------------------------------------------------------------------------------
// Query 9: SalesCategory (5 rows, Grain: 1 row per product category)
// -------------------------------------------------------------------------------
let
    Source = Csv.Document(File.Contents(SourceFolder & "sales_category.csv"), [Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.None]),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"category", type text},
        {"units_sold", Int64.Type},
        {"transaction_count", Int64.Type},
        {"calculated_revenue", type number},
        {"average_units_per_transaction", type number}
    })
in
    TypedTable
