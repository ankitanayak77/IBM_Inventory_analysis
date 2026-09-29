"""
Smart Inventory & Sales Analysis System - Power BI Project Generator
--------------------------------------------------------------------
Phase 13: Assembles the .pbip (Power BI Project), Dataset (model.bim),
and Report (report.json) artifacts for direct import into Power BI Desktop.

Features:
- Completely portable data source references via 'SourceFolder' parameter
- Clean Star-Schema design with strictly 1-direction filtering (no bidirectional filter paths)
- 9 fully typed tables with proper M partitions and DAX measures
"""

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
POWERBI_DIR = BASE_DIR / "powerbi"
DATASET_DIR = POWERBI_DIR / "SmartInventory_Analytics.Dataset"
REPORT_DIR = POWERBI_DIR / "SmartInventory_Analytics.Report"

DATASET_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def build_pbip():
    # 1. SmartInventory_Analytics.pbip
    pbip_content = {
        "version": "1.0",
        "artifacts": [
            {
                "report": {
                    "path": "SmartInventory_Analytics.Report"
                }
            }
        ],
        "settings": {
            "enableAutoAuth": True
        }
    }
    (POWERBI_DIR / "SmartInventory_Analytics.pbip").write_text(json.dumps(pbip_content, indent=2), encoding="utf-8")

    # 2. definition.pbidataset
    pbidataset = {
        "version": "1.0",
        "datasetReference": {
            "byPath": None,
            "byConnection": None
        }
    }
    (DATASET_DIR / "definition.pbidataset").write_text(json.dumps(pbidataset, indent=2), encoding="utf-8")

    # 3. model.bim (Tabular Model Schema)
    bim = {
        "name": "SmartInventory_Analytics",
        "compatibilityLevel": 1567,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True
            },
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "expressions": [
                {
                    "name": "SourceFolder",
                    "kind": "m",
                    "expression": [
                        "let",
                        "    // Configurable parameter pointing to exports/powerbi directory",
                        "    // Defaults to relative path \"..\\exports\\powerbi\\\" from project directory,",
                        "    // or can be customized to any absolute path in Power Query Parameters",
                        "    Folder = \"..\\\\exports\\\\powerbi\\\\\"",
                        "in",
                        "    Folder meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]"
                    ]
                }
            ],
            "tables": [
                {
                    "name": "DimDate",
                    "dataCategory": "Time",
                    "columns": [
                        {"name": "date", "dataType": "dateTime", "isKey": True, "formatString": "yyyy-mm-dd", "sourceColumn": "date"},
                        {"name": "year", "dataType": "int64", "formatString": "0", "sourceColumn": "year"},
                        {"name": "month_number", "dataType": "int64", "formatString": "0", "sourceColumn": "month_number"},
                        {"name": "month_name", "dataType": "string", "sourceColumn": "month_name", "sortByColumn": "month_number"},
                        {"name": "quarter", "dataType": "string", "sourceColumn": "quarter"},
                        {"name": "year_month", "dataType": "string", "sourceColumn": "year_month"},
                        {"name": "day", "dataType": "int64", "formatString": "0", "sourceColumn": "day"},
                        {"name": "day_of_week", "dataType": "string", "sourceColumn": "day_of_week"}
                    ],
                    "partitions": [{
                        "name": "DimDate-Partition",
                        "mode": "import",
                        "source": {
                            "type": "m",
                            "expression": [
                                "let",
                                '    Source = Csv.Document(File.Contents(SourceFolder & "dim_date.csv"), [Delimiter=",", Columns=8, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                '    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                '    Typed = Table.TransformColumnTypes(PromotedHeaders, {{"date", type date}, {"year", Int64.Type}, {"month_number", Int64.Type}, {"month_name", type text}, {"quarter", type text}, {"year_month", type text}, {"day", Int64.Type}, {"day_of_week", type text}})',
                                "in",
                                "    Typed"
                            ]
                        }
                    }]
                },
                {
                    "name": "DimProducts",
                    "columns": [
                        {"name": "product_id", "dataType": "int64", "isKey": True, "formatString": "0", "sourceColumn": "product_id"},
                        {"name": "product_name", "dataType": "string", "sourceColumn": "product_name"},
                        {"name": "category", "dataType": "string", "sourceColumn": "category"},
                        {"name": "cost_price", "dataType": "double", "formatString": "$#,##0.00", "sourceColumn": "cost_price"},
                        {"name": "selling_price", "dataType": "double", "formatString": "$#,##0.00", "sourceColumn": "selling_price"}
                    ],
                    "partitions": [{
                        "name": "DimProducts-Partition",
                        "mode": "import",
                        "source": {
                            "type": "m",
                            "expression": [
                                "let",
                                '    Source = Csv.Document(File.Contents(SourceFolder & "dim_products.csv"), [Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                '    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                '    Typed = Table.TransformColumnTypes(PromotedHeaders, {{"product_id", Int64.Type}, {"product_name", type text}, {"category", type text}, {"cost_price", type number}, {"selling_price", type number}})',
                                "in",
                                "    Typed"
                            ]
                        }
                    }]
                },
                {
                    "name": "DimStores",
                    "columns": [
                        {"name": "store_id", "dataType": "int64", "isKey": True, "formatString": "0", "sourceColumn": "store_id"},
                        {"name": "store_name", "dataType": "string", "sourceColumn": "store_name"},
                        {"name": "city", "dataType": "string", "sourceColumn": "city"},
                        {"name": "location", "dataType": "string", "sourceColumn": "location"},
                        {"name": "open_date", "dataType": "dateTime", "formatString": "yyyy-mm-dd", "sourceColumn": "open_date"}
                    ],
                    "partitions": [{
                        "name": "DimStores-Partition",
                        "mode": "import",
                        "source": {
                            "type": "m",
                            "expression": [
                                "let",
                                '    Source = Csv.Document(File.Contents(SourceFolder & "dim_stores.csv"), [Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                '    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                '    Typed = Table.TransformColumnTypes(PromotedHeaders, {{"store_id", Int64.Type}, {"store_name", type text}, {"city", type text}, {"location", type text}, {"open_date", type date}})',
                                "in",
                                "    Typed"
                            ]
                        }
                    }]
                },
                {
                    "name": "FactSalesDaily",
                    "columns": [
                        {"name": "sale_date", "dataType": "dateTime", "formatString": "yyyy-mm-dd", "sourceColumn": "sale_date"},
                        {"name": "units_sold", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "units_sold"},
                        {"name": "transaction_count", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "transaction_count"},
                        {"name": "calculated_revenue", "dataType": "double", "formatString": "$#,##0.00", "sourceColumn": "calculated_revenue"}
                    ],
                    "measures": [
                        {
                            "name": "Total Units Sold",
                            "expression": "SUM(FactSalesDaily[units_sold])",
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Total Calculated Revenue",
                            "expression": "SUM(FactSalesDaily[calculated_revenue])",
                            "formatString": "$#,##0.00"
                        },
                        {
                            "name": "Transaction Count",
                            "expression": "SUM(FactSalesDaily[transaction_count])",
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Average Units per Transaction",
                            "expression": "DIVIDE([Total Units Sold], [Transaction Count], 0)",
                            "formatString": "0.00"
                        },
                        {
                            "name": "Average Daily Sales",
                            "expression": "AVERAGEX(VALUES(DimDate[date]), [Total Units Sold])",
                            "formatString": "#,##0.0"
                        },
                        {
                            "name": "Average Daily Revenue",
                            "expression": "AVERAGEX(VALUES(DimDate[date]), [Total Calculated Revenue])",
                            "formatString": "$#,##0.00"
                        }
                    ],
                    "partitions": [{
                        "name": "FactSalesDaily-Partition",
                        "mode": "import",
                        "source": {
                            "type": "m",
                            "expression": [
                                "let",
                                '    Source = Csv.Document(File.Contents(SourceFolder & "sales_daily.csv"), [Delimiter=",", Columns=4, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                '    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                '    Typed = Table.TransformColumnTypes(PromotedHeaders, {{"sale_date", type date}, {"units_sold", Int64.Type}, {"transaction_count", Int64.Type}, {"calculated_revenue", type number}})',
                                "in",
                                "    Typed"
                            ]
                        }
                    }]
                },
                {
                    "name": "FactInventorySnapshot",
                    "columns": [
                        {"name": "inventory_id", "dataType": "int64", "isKey": True, "formatString": "0", "sourceColumn": "inventory_id"},
                        {"name": "store_id", "dataType": "int64", "formatString": "0", "sourceColumn": "store_id"},
                        {"name": "store_name", "dataType": "string", "sourceColumn": "store_name"},
                        {"name": "city", "dataType": "string", "sourceColumn": "city"},
                        {"name": "product_id", "dataType": "int64", "formatString": "0", "sourceColumn": "product_id"},
                        {"name": "product_name", "dataType": "string", "sourceColumn": "product_name"},
                        {"name": "category", "dataType": "string", "sourceColumn": "category"},
                        {"name": "stock_on_hand", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "stock_on_hand"},
                        {"name": "reorder_level", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "reorder_level"},
                        {"name": "stock_status", "dataType": "string", "sourceColumn": "stock_status"},
                        {"name": "inventory_value", "dataType": "double", "formatString": "$#,##0.00", "sourceColumn": "inventory_value"}
                    ],
                    "measures": [
                        {
                            "name": "Total Current Stock",
                            "expression": "SUM(FactInventorySnapshot[stock_on_hand])",
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Inventory Value",
                            "expression": "SUM(FactInventorySnapshot[inventory_value])",
                            "formatString": "$#,##0.00"
                        },
                        {
                            "name": "Total SKU Combinations",
                            "expression": "COUNTROWS(FactInventorySnapshot)",
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Normal Stock Count",
                            "expression": 'CALCULATE(COUNTROWS(FactInventorySnapshot), FactInventorySnapshot[stock_status] = "NORMAL")',
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Low Stock Count",
                            "expression": 'CALCULATE(COUNTROWS(FactInventorySnapshot), FactInventorySnapshot[stock_status] = "LOW STOCK")',
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Out of Stock Count",
                            "expression": 'CALCULATE(COUNTROWS(FactInventorySnapshot), FactInventorySnapshot[stock_status] = "OUT OF STOCK")',
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Percent Low Stock",
                            "expression": "DIVIDE([Low Stock Count], [Total SKU Combinations], 0)",
                            "formatString": "0.0%"
                        },
                        {
                            "name": "Percent Out of Stock",
                            "expression": "DIVIDE([Out of Stock Count], [Total SKU Combinations], 0)",
                            "formatString": "0.0%"
                        }
                    ],
                    "partitions": [{
                        "name": "FactInventorySnapshot-Partition",
                        "mode": "import",
                        "source": {
                            "type": "m",
                            "expression": [
                                "let",
                                '    Source = Csv.Document(File.Contents(SourceFolder & "inventory_snapshot.csv"), [Delimiter=",", Columns=11, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                '    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                '    Typed = Table.TransformColumnTypes(PromotedHeaders, {{"inventory_id", Int64.Type}, {"store_id", Int64.Type}, {"store_name", type text}, {"city", type text}, {"product_id", Int64.Type}, {"product_name", type text}, {"category", type text}, {"stock_on_hand", Int64.Type}, {"reorder_level", Int64.Type}, {"stock_status", type text}, {"inventory_value", type number}})',
                                "in",
                                "    Typed"
                            ]
                        }
                    }]
                },
                {
                    "name": "ProductMovement",
                    "columns": [
                        {"name": "product_id", "dataType": "int64", "isKey": True, "formatString": "0", "sourceColumn": "product_id"},
                        {"name": "product_name", "dataType": "string", "sourceColumn": "product_name"},
                        {"name": "category", "dataType": "string", "sourceColumn": "category"},
                        {"name": "units_sold", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "units_sold"},
                        {"name": "transactions", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "transactions"},
                        {"name": "sales_velocity", "dataType": "double", "formatString": "0.00", "sourceColumn": "sales_velocity"},
                        {"name": "movement_status", "dataType": "string", "sourceColumn": "movement_status"},
                        {"name": "current_stock", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "current_stock"},
                        {"name": "reorder_level", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "reorder_level"},
                        {"name": "stock_coverage_days", "dataType": "double", "formatString": "0.0", "sourceColumn": "stock_coverage_days"}
                    ],
                    "measures": [
                        {
                            "name": "Fast Moving Product Count",
                            "expression": 'CALCULATE(COUNTROWS(ProductMovement), ProductMovement[movement_status] = "FAST MOVING")',
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Normal Moving Product Count",
                            "expression": 'CALCULATE(COUNTROWS(ProductMovement), ProductMovement[movement_status] = "NORMAL")',
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Slow Moving Product Count",
                            "expression": 'CALCULATE(COUNTROWS(ProductMovement), ProductMovement[movement_status] = "SLOW MOVING")',
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Average Sales Velocity",
                            "expression": "AVERAGE(ProductMovement[sales_velocity])",
                            "formatString": "0.00"
                        }
                    ],
                    "partitions": [{
                        "name": "ProductMovement-Partition",
                        "mode": "import",
                        "source": {
                            "type": "m",
                            "expression": [
                                "let",
                                '    Source = Csv.Document(File.Contents(SourceFolder & "product_movement.csv"), [Delimiter=",", Columns=10, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                '    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                '    Typed = Table.TransformColumnTypes(PromotedHeaders, {{"product_id", Int64.Type}, {"product_name", type text}, {"category", type text}, {"units_sold", Int64.Type}, {"transactions", Int64.Type}, {"sales_velocity", type number}, {"movement_status", type text}, {"current_stock", Int64.Type}, {"reorder_level", Int64.Type}, {"stock_coverage_days", type number}})',
                                "in",
                                "    Typed"
                            ]
                        }
                    }]
                },
                {
                    "name": "Recommendations",
                    "columns": [
                        {"name": "product_id", "dataType": "int64", "isKey": True, "formatString": "0", "sourceColumn": "product_id"},
                        {"name": "product_name", "dataType": "string", "sourceColumn": "product_name"},
                        {"name": "category", "dataType": "string", "sourceColumn": "category"},
                        {"name": "movement_status", "dataType": "string", "sourceColumn": "movement_status"},
                        {"name": "current_stock", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "current_stock"},
                        {"name": "reorder_level", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "reorder_level"},
                        {"name": "sales_velocity", "dataType": "double", "formatString": "0.00", "sourceColumn": "sales_velocity"},
                        {"name": "stock_coverage_days", "dataType": "double", "formatString": "0.0", "sourceColumn": "stock_coverage_days"},
                        {"name": "recommendation", "dataType": "string", "sourceColumn": "recommendation"},
                        {"name": "reason", "dataType": "string", "sourceColumn": "reason"},
                        {"name": "priority", "dataType": "string", "sourceColumn": "priority"}
                    ],
                    "measures": [
                        {
                            "name": "Products Requiring Attention",
                            "expression": 'CALCULATE(COUNTROWS(Recommendations), Recommendations[priority] IN {"HIGH", "MEDIUM"})',
                            "formatString": "#,##0"
                        },
                        {
                            "name": "High Priority Recommendations",
                            "expression": 'CALCULATE(COUNTROWS(Recommendations), Recommendations[priority] = "HIGH")',
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Medium Priority Recommendations",
                            "expression": 'CALCULATE(COUNTROWS(Recommendations), Recommendations[priority] = "MEDIUM")',
                            "formatString": "#,##0"
                        },
                        {
                            "name": "Low Priority Recommendations",
                            "expression": 'CALCULATE(COUNTROWS(Recommendations), Recommendations[priority] = "LOW")',
                            "formatString": "#,##0"
                        },
                        {
                            "name": "No Priority Recommendations",
                            "expression": 'CALCULATE(COUNTROWS(Recommendations), Recommendations[priority] = "NONE")',
                            "formatString": "#,##0"
                        }
                    ],
                    "partitions": [{
                        "name": "Recommendations-Partition",
                        "mode": "import",
                        "source": {
                            "type": "m",
                            "expression": [
                                "let",
                                '    Source = Csv.Document(File.Contents(SourceFolder & "recommendations.csv"), [Delimiter=",", Columns=11, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                '    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                '    Typed = Table.TransformColumnTypes(PromotedHeaders, {{"product_id", Int64.Type}, {"product_name", type text}, {"category", type text}, {"movement_status", type text}, {"current_stock", Int64.Type}, {"reorder_level", Int64.Type}, {"sales_velocity", type number}, {"stock_coverage_days", type number}, {"recommendation", type text}, {"reason", type text}, {"priority", type text}})',
                                "in",
                                "    Typed"
                            ]
                        }
                    }]
                },
                {
                    "name": "FactStoreSales",
                    "columns": [
                        {"name": "store_id", "dataType": "int64", "isKey": True, "formatString": "0", "sourceColumn": "store_id"},
                        {"name": "store_name", "dataType": "string", "sourceColumn": "store_name"},
                        {"name": "city", "dataType": "string", "sourceColumn": "city"},
                        {"name": "units_sold", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "units_sold"},
                        {"name": "transaction_count", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "transaction_count"},
                        {"name": "calculated_revenue", "dataType": "double", "formatString": "$#,##0.00", "sourceColumn": "calculated_revenue"}
                    ],
                    "partitions": [{
                        "name": "FactStoreSales-Partition",
                        "mode": "import",
                        "source": {
                            "type": "m",
                            "expression": [
                                "let",
                                '    Source = Csv.Document(File.Contents(SourceFolder & "store_sales.csv"), [Delimiter=",", Columns=6, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                '    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                '    Typed = Table.TransformColumnTypes(PromotedHeaders, {{"store_id", Int64.Type}, {"store_name", type text}, {"city", type text}, {"units_sold", Int64.Type}, {"transaction_count", Int64.Type}, {"calculated_revenue", type number}})',
                                "in",
                                "    Typed"
                            ]
                        }
                    }]
                },
                {
                    "name": "SalesCategory",
                    "columns": [
                        {"name": "category", "dataType": "string", "isKey": True, "sourceColumn": "category"},
                        {"name": "units_sold", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "units_sold"},
                        {"name": "transaction_count", "dataType": "int64", "formatString": "#,##0", "sourceColumn": "transaction_count"},
                        {"name": "calculated_revenue", "dataType": "double", "formatString": "$#,##0.00", "sourceColumn": "calculated_revenue"},
                        {"name": "average_units_per_transaction", "dataType": "double", "formatString": "0.00", "sourceColumn": "average_units_per_transaction"}
                    ],
                    "partitions": [{
                        "name": "SalesCategory-Partition",
                        "mode": "import",
                        "source": {
                            "type": "m",
                            "expression": [
                                "let",
                                '    Source = Csv.Document(File.Contents(SourceFolder & "sales_category.csv"), [Delimiter=",", Columns=5, Encoding=65001, QuoteStyle=QuoteStyle.None]),',
                                '    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),',
                                '    Typed = Table.TransformColumnTypes(PromotedHeaders, {{"category", type text}, {"units_sold", Int64.Type}, {"transaction_count", Int64.Type}, {"calculated_revenue", type number}, {"average_units_per_transaction", type number}})',
                                "in",
                                "    Typed"
                            ]
                        }
                    }]
                }
            ],
            "relationships": [
                {
                    "name": "Rel_Date_SalesDaily",
                    "fromTable": "FactSalesDaily",
                    "fromColumn": "sale_date",
                    "toTable": "DimDate",
                    "toColumn": "date",
                    "crossFilteringBehavior": "oneDirection"
                },
                {
                    "name": "Rel_Product_Inventory",
                    "fromTable": "FactInventorySnapshot",
                    "fromColumn": "product_id",
                    "toTable": "DimProducts",
                    "toColumn": "product_id",
                    "crossFilteringBehavior": "oneDirection"
                },
                {
                    "name": "Rel_Store_Inventory",
                    "fromTable": "FactInventorySnapshot",
                    "fromColumn": "store_id",
                    "toTable": "DimStores",
                    "toColumn": "store_id",
                    "crossFilteringBehavior": "oneDirection"
                },
                {
                    "name": "Rel_Product_Movement",
                    "fromTable": "ProductMovement",
                    "fromColumn": "product_id",
                    "toTable": "DimProducts",
                    "toColumn": "product_id",
                    "crossFilteringBehavior": "oneDirection"
                },
                {
                    "name": "Rel_Product_Recommendations",
                    "fromTable": "Recommendations",
                    "fromColumn": "product_id",
                    "toTable": "DimProducts",
                    "toColumn": "product_id",
                    "crossFilteringBehavior": "oneDirection"
                },
                {
                    "name": "Rel_Store_Sales",
                    "fromTable": "FactStoreSales",
                    "fromColumn": "store_id",
                    "toTable": "DimStores",
                    "toColumn": "store_id",
                    "crossFilteringBehavior": "oneDirection"
                }
            ]
        }
    }
    (DATASET_DIR / "model.bim").write_text(json.dumps(bim, indent=2), encoding="utf-8")

    # 4. definition.pbir
    pbir = {
        "version": "1.0",
        "datasetReference": {
            "byPath": {
                "path": "../SmartInventory_Analytics.Dataset"
            },
            "byConnection": None
        }
    }
    (REPORT_DIR / "definition.pbir").write_text(json.dumps(pbir, indent=2), encoding="utf-8")

    # 5. report.json (Standard Power BI visual layout with 5 distinct analytical pages)
    report_json = {
        "config": json.dumps({
            "version": "5.50",
            "themeCollection": {
                "baseTheme": {
                    "name": "Executive Dark/Slate",
                    "version": "2.0",
                    "type": 2
                }
            },
            "activeSectionIndex": 0,
            "defaultDrillFilterOtherVisuals": True
        }),
        "layoutOptimization": 0,
        "sections": [
            {
                "id": 0,
                "name": "Section_ExecutiveOverview",
                "displayName": "1. Executive Overview",
                "filters": "[]",
                "height": 900,
                "width": 1600,
                "config": json.dumps({
                    "objects": {
                        "background": [{
                            "properties": {
                                "color": {"solid": {"color": "#0F172A"}},
                                "transparency": 0
                            }
                        }]
                    }
                })
            },
            {
                "id": 1,
                "name": "Section_SalesAnalysis",
                "displayName": "2. Sales Analysis",
                "filters": "[]",
                "height": 900,
                "width": 1600,
                "config": json.dumps({
                    "objects": {
                        "background": [{
                            "properties": {
                                "color": {"solid": {"color": "#0F172A"}},
                                "transparency": 0
                            }
                        }]
                    }
                })
            },
            {
                "id": 2,
                "name": "Section_InventoryAnalysis",
                "displayName": "3. Current Inventory Analysis",
                "filters": "[]",
                "height": 900,
                "width": 1600,
                "config": json.dumps({
                    "objects": {
                        "background": [{
                            "properties": {
                                "color": {"solid": {"color": "#0F172A"}},
                                "transparency": 0
                            }
                        }]
                    }
                })
            },
            {
                "id": 3,
                "name": "Section_ProductMovement",
                "displayName": "4. Product Movement",
                "filters": "[]",
                "height": 900,
                "width": 1600,
                "config": json.dumps({
                    "objects": {
                        "background": [{
                            "properties": {
                                "color": {"solid": {"color": "#0F172A"}},
                                "transparency": 0
                            }
                        }]
                    }
                })
            },
            {
                "id": 4,
                "name": "Section_Recommendations",
                "displayName": "5. Recommendations",
                "filters": "[]",
                "height": 900,
                "width": 1600,
                "config": json.dumps({
                    "objects": {
                        "background": [{
                            "properties": {
                                "color": {"solid": {"color": "#0F172A"}},
                                "transparency": 0
                            }
                        }]
                    }
                })
            }
        ]
    }
    (REPORT_DIR / "report.json").write_text(json.dumps(report_json, indent=2), encoding="utf-8")
    print("Portable Power BI Project assembled successfully in powerbi/!")

if __name__ == "__main__":
    build_pbip()
