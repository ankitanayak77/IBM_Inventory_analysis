/**
 * Smart Inventory & Sales Analysis System - Dashboard Visual Analytics
 * ---------------------------------------------------------------------
 * Phase 11: Interactive Dashboard Charts & Visual Analytics
 * 
 * Manages Chart.js instances and asynchronous API updates for:
 * 1. Sales Units Trend (Line)
 * 2. Calculated Revenue Trend (Line / Bar)
 * 3. Sales by Category (Doughnut / Bar)
 * 4. Top 10 Products by Units Sold (Horizontal Bar)
 * 5. Current Inventory Stock Status (Doughnut)
 * 6. Inventory Units by Category (Bar)
 * 7. Store Sales Performance (Bar with Top 5 / 10 / All selector)
 * 8. Product Movement Distribution (Doughnut)
 * 9. Recommendation Signal Summary (Bar / Polar)
 */

(function () {
    "use strict";

    // Chart.js instances registry for clean destruction & re-rendering
    const charts = {};

    // Standard curated color palette matching the application design system
    const PALETTE = {
        primary: "#6366f1",
        primaryBg: "rgba(99, 102, 241, 0.15)",
        primaryBorder: "#4f46e5",
        cyan: "#06b6d4",
        cyanBg: "rgba(6, 182, 212, 0.15)",
        emerald: "#10b981",
        emeraldBg: "rgba(16, 185, 129, 0.15)",
        amber: "#f59e0b",
        amberBg: "rgba(245, 158, 11, 0.15)",
        rose: "#ef4444",
        roseBg: "rgba(239, 68, 68, 0.15)",
        purple: "#8b5cf6",
        purpleBg: "rgba(139, 92, 246, 0.15)",
        slate: "#64748b",
        gridLine: "#e2e8f0",
        categoryColors: [
            "#6366f1", // Art & Crafts (Indigo)
            "#06b6d4", // Toys (Cyan)
            "#10b981", // Games (Emerald)
            "#f59e0b", // Sports & Outdoors (Amber)
            "#8b5cf6"  // Electronics (Purple)
        ]
    };

    /**
     * Helper to retrieve active filter values from the toolbar
     */
    function getActiveFilters() {
        const presetEl = document.getElementById("filter-preset");
        const startEl = document.getElementById("filter-start-date");
        const endEl = document.getElementById("filter-end-date");
        const categoryEl = document.getElementById("filter-category");
        const storeEl = document.getElementById("filter-store");

        return {
            preset: presetEl ? presetEl.value : "full",
            start_date: startEl ? startEl.value : "",
            end_date: endEl ? endEl.value : "",
            category: categoryEl ? categoryEl.value : "all",
            store_id: storeEl ? storeEl.value : "all"
        };
    }

    /**
     * Safely destroy an existing Chart.js instance
     */
    function destroyChart(name) {
        if (charts[name]) {
            charts[name].destroy();
            charts[name] = null;
        }
    }

    /**
     * Toggle chart loading state
     */
    function setLoading(containerId, isLoading) {
        const wrap = document.getElementById(containerId);
        if (!wrap) return;
        let overlay = wrap.querySelector(".chart-loading-overlay");
        if (isLoading) {
            if (!overlay) {
                overlay = document.createElement("div");
                overlay.className = "chart-loading-overlay";
                overlay.innerHTML = '<div class="spinner"></div><span style="font-size:0.8rem; color:#64748b; margin-top:8px;">Loading data...</span>';
                wrap.style.position = "relative";
                wrap.appendChild(overlay);
            }
        } else {
            if (overlay) overlay.remove();
        }
    }

    /**
     * Render empty state inside chart wrapper
     */
    function showEmptyState(canvasId, message) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const parent = canvas.parentElement;
        let emptyEl = parent.querySelector(".chart-empty-state");
        if (!emptyEl) {
            emptyEl = document.createElement("div");
            emptyEl.className = "chart-empty-state";
            emptyEl.style.cssText = "display:flex; flex-direction:column; align-items:center; justify-content:center; height:240px; color:#94a3b8; font-size:0.875rem;";
            emptyEl.innerHTML = `<span style="font-size:2rem; margin-bottom:6px;">📊</span><span>${message || "No data recorded for this selection"}</span>`;
            canvas.style.display = "none";
            parent.appendChild(emptyEl);
        }
    }

    /**
     * Clear empty state and restore canvas
     */
    function clearEmptyState(canvasId) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        canvas.style.display = "block";
        const emptyEl = canvas.parentElement.querySelector(".chart-empty-state");
        if (emptyEl) emptyEl.remove();
    }

    // ==========================================================
    // 1. CHART: SALES TREND (Units Sold)
    async function loadSalesTrend() {
        const canvas = document.getElementById("chart-sales-trend");
        if (!canvas) return;

        setLoading("sales-trend-wrap", true);
        const f = getActiveFilters();
        const url = `/api/dashboard/sales-trend?preset=${f.preset}&start_date=${f.start_date}&end_date=${f.end_date}&category=${encodeURIComponent(f.category)}&store_id=${f.store_id}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            setLoading("sales-trend-wrap", false);
            destroyChart("salesTrend");

            if (!data.labels || data.labels.length === 0) {
                showEmptyState("chart-sales-trend", "No sales records in selected date range.");
                return;
            }
            clearEmptyState("chart-sales-trend");

            // Format subtitle / period indicator
            const periodBadge = document.getElementById("sales-trend-period");
            if (periodBadge) {
                periodBadge.textContent = `${data.start_date} to ${data.end_date} (${data.labels.length} points | ${data.total_units.toLocaleString()} units)`;
            }

            const ctx = canvas.getContext("2d");
            charts.salesTrend = new Chart(ctx, {
                type: "line",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Units Sold",
                        data: data.units,
                        borderColor: PALETTE.primary,
                        backgroundColor: PALETTE.primaryBg,
                        borderWidth: 2,
                        pointRadius: data.labels.length > 90 ? 0 : 3,
                        pointHoverRadius: 5,
                        fill: true,
                        tension: 0.2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: "index", intersect: false },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `Units Sold: ${ctx.parsed.y.toLocaleString()}`
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: {
                                maxTicksLimit: 12,
                                color: PALETTE.slate,
                                font: { size: 11 }
                            }
                        },
                        y: {
                            beginAtZero: true,
                            grid: { color: PALETTE.gridLine },
                            ticks: {
                                color: PALETTE.slate,
                                callback: (v) => v.toLocaleString()
                            }
                        }
                    }
                }
            });
        } catch (err) {
            setLoading("sales-trend-wrap", false);
            console.error("Error loading sales trend:", err);
        }
    }

    async function loadRevenueTrend() {
        const canvas = document.getElementById("chart-revenue-trend");
        if (!canvas) return;

        setLoading("revenue-trend-wrap", true);
        const f = getActiveFilters();
        const url = `/api/dashboard/revenue-trend?preset=${f.preset}&start_date=${f.start_date}&end_date=${f.end_date}&category=${encodeURIComponent(f.category)}&store_id=${f.store_id}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            setLoading("revenue-trend-wrap", false);
            destroyChart("revenueTrend");

            if (!data.labels || data.labels.length === 0) {
                showEmptyState("chart-revenue-trend", "No revenue recorded for selected range.");
                return;
            }
            clearEmptyState("chart-revenue-trend");

            const periodBadge = document.getElementById("revenue-trend-period");
            if (periodBadge) {
                periodBadge.textContent = `$${data.total_revenue.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})} total`;
            }

            const ctx = canvas.getContext("2d");
            charts.revenueTrend = new Chart(ctx, {
                type: "line",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Calculated Revenue ($)",
                        data: data.data,
                        borderColor: PALETTE.emerald,
                        backgroundColor: PALETTE.emeraldBg,
                        borderWidth: 2,
                        pointRadius: data.labels.length > 90 ? 0 : 3,
                        pointHoverRadius: 5,
                        fill: true,
                        tension: 0.2
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: { mode: "index", intersect: false },
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `Calculated Revenue: $${ctx.parsed.y.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: {
                                maxTicksLimit: 12,
                                color: PALETTE.slate,
                                font: { size: 11 }
                            }
                        },
                        y: {
                            beginAtZero: true,
                            grid: { color: PALETTE.gridLine },
                            ticks: {
                                color: PALETTE.slate,
                                callback: (v) => `$${(v >= 1000 ? (v / 1000).toFixed(0) + "k" : v)}`
                            }
                        }
                    }
                }
            });
        } catch (err) {
            setLoading("revenue-trend-wrap", false);
            console.error("Error loading revenue trend:", err);
        }
    }

    // ==========================================================
    // 3. CHART: SALES BY CATEGORY (Units & Revenue)
    // ==========================================================
    async function loadCategorySales() {
        const canvas = document.getElementById("chart-category-sales");
        if (!canvas) return;

        setLoading("category-sales-wrap", true);
        const f = getActiveFilters();
        const url = `/api/dashboard/category-sales?preset=${f.preset}&start_date=${f.start_date}&end_date=${f.end_date}&store_id=${f.store_id}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            setLoading("category-sales-wrap", false);
            destroyChart("categorySales");

            if (!data.labels || data.labels.length === 0) {
                showEmptyState("chart-category-sales", "No category sales records found.");
                return;
            }
            clearEmptyState("chart-category-sales");

            const ctx = canvas.getContext("2d");
            charts.categorySales = new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.units,
                        backgroundColor: PALETTE.categoryColors,
                        borderWidth: 2,
                        borderColor: "#ffffff"
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: { boxWidth: 12, font: { size: 11 }, padding: 12 }
                        },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => {
                                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                    const val = ctx.raw;
                                    const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                    return ` ${ctx.label}: ${val.toLocaleString()} units (${pct}%)`;
                                }
                            }
                        }
                    },
                    cutout: "62%"
                }
            });
        } catch (err) {
            setLoading("category-sales-wrap", false);
            console.error("Error loading category sales:", err);
        }
    }

    // ==========================================================
    // 4. CHART: TOP 10 PRODUCTS BY UNITS SOLD
    // ==========================================================
    async function loadTopProducts() {
        const canvas = document.getElementById("chart-top-products");
        if (!canvas) return;

        setLoading("top-products-wrap", true);
        const f = getActiveFilters();
        const url = `/api/dashboard/top-products?preset=${f.preset}&start_date=${f.start_date}&end_date=${f.end_date}&category=${encodeURIComponent(f.category)}&store_id=${f.store_id}&limit=10`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            setLoading("top-products-wrap", false);
            destroyChart("topProducts");

            if (!data.labels || data.labels.length === 0) {
                showEmptyState("chart-top-products", "No top products recorded.");
                return;
            }
            clearEmptyState("chart-top-products");

            const ctx = canvas.getContext("2d");
            const labelsRev = [...data.labels].reverse();
            const unitsRev = [...data.units].reverse();

            charts.topProducts = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: labelsRev,
                    datasets: [{
                        label: "Units Sold",
                        data: unitsRev,
                        backgroundColor: PALETTE.primary,
                        borderRadius: 4,
                        maxBarThickness: 18
                    }]
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `Units Sold: ${ctx.parsed.x.toLocaleString()}`
                            }
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            grid: { color: PALETTE.gridLine },
                            ticks: {
                                color: PALETTE.slate,
                                callback: (v) => v >= 1000 ? (v / 1000).toFixed(0) + "k" : v
                            }
                        },
                        y: {
                            grid: { display: false },
                            ticks: {
                                color: PALETTE.slate,
                                font: { size: 11 }
                            }
                        }
                    }
                }
            });
        } catch (err) {
            setLoading("top-products-wrap", false);
            console.error("Error loading top products:", err);
        }
    }

    // ==========================================================
    // 5. CHART: CURRENT INVENTORY STATUS
    // ==========================================================
    async function loadInventoryStatus() {
        const canvas = document.getElementById("chart-inventory-status");
        if (!canvas) return;

        setLoading("inventory-status-wrap", true);
        const f = getActiveFilters();
        const url = `/api/dashboard/inventory-status?category=${encodeURIComponent(f.category)}&store_id=${f.store_id}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            setLoading("inventory-status-wrap", false);
            destroyChart("inventoryStatus");

            const ctx = canvas.getContext("2d");
            charts.inventoryStatus = new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.counts,
                        backgroundColor: [PALETTE.emerald, PALETTE.amber, PALETTE.rose],
                        borderWidth: 2,
                        borderColor: "#ffffff"
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: { boxWidth: 12, font: { size: 11 }, padding: 12 }
                        },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => {
                                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                    const val = ctx.raw;
                                    const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                    return ` ${ctx.label}: ${val.toLocaleString()} store-SKUs (${pct}%)`;
                                }
                            }
                        }
                    },
                    cutout: "62%"
                }
            });
        } catch (err) {
            setLoading("inventory-status-wrap", false);
            console.error("Error loading inventory status:", err);
        }
    }

    // ==========================================================
    // 6. CHART: INVENTORY UNITS BY CATEGORY
    // ==========================================================
    async function loadInventoryCategories() {
        const canvas = document.getElementById("chart-inventory-categories");
        if (!canvas) return;

        setLoading("inventory-cat-wrap", true);
        const f = getActiveFilters();
        const url = `/api/dashboard/inventory-category?store_id=${f.store_id}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            setLoading("inventory-cat-wrap", false);
            destroyChart("inventoryCategories");

            const ctx = canvas.getContext("2d");
            charts.inventoryCategories = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Stock on Hand",
                        data: data.units,
                        backgroundColor: PALETTE.cyan,
                        borderRadius: 4,
                        maxBarThickness: 28
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `Stock on Hand: ${ctx.parsed.y.toLocaleString()} units`
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: { color: PALETTE.slate, font: { size: 11 } }
                        },
                        y: {
                            beginAtZero: true,
                            grid: { color: PALETTE.gridLine },
                            ticks: {
                                color: PALETTE.slate,
                                callback: (v) => v.toLocaleString()
                            }
                        }
                    }
                }
            });
        } catch (err) {
            setLoading("inventory-cat-wrap", false);
            console.error("Error loading inventory categories:", err);
        }
    }

    // ==========================================================
    // 7. CHART: SALES BY STORE BRANCH
    // ==========================================================
    async function loadStoreSales() {
        const canvas = document.getElementById("chart-store-sales");
        if (!canvas) return;

        setLoading("store-sales-wrap", true);
        const f = getActiveFilters();
        const limitSelect = document.getElementById("store-limit-select");
        const limit = limitSelect ? limitSelect.value : "10";

        const url = `/api/dashboard/store-sales?preset=${f.preset}&start_date=${f.start_date}&end_date=${f.end_date}&category=${encodeURIComponent(f.category)}&limit=${limit}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            setLoading("store-sales-wrap", false);
            destroyChart("storeSales");

            if (!data.labels || data.labels.length === 0) {
                showEmptyState("chart-store-sales", "No store sales records found.");
                return;
            }
            clearEmptyState("chart-store-sales");

            const ctx = canvas.getContext("2d");
            charts.storeSales = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: data.labels,
                    datasets: [
                        {
                            label: "Units Sold",
                            data: data.units,
                            backgroundColor: PALETTE.primary,
                            borderRadius: 4,
                            yAxisID: "y"
                        },
                        {
                            label: "Calculated Revenue ($)",
                            data: data.revenue,
                            backgroundColor: PALETTE.emerald,
                            borderRadius: 4,
                            yAxisID: "y1"
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "top",
                            labels: { boxWidth: 12, font: { size: 11 } }
                        },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => {
                                    if (ctx.datasetIndex === 0) {
                                        return `Units: ${ctx.parsed.y.toLocaleString()}`;
                                    } else {
                                        return `Calculated Revenue: $${ctx.parsed.y.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
                                    }
                                }
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { display: false },
                            ticks: {
                                maxRotation: 45,
                                minRotation: 0,
                                color: PALETTE.slate,
                                font: { size: 10 }
                            }
                        },
                        y: {
                            type: "linear",
                            position: "left",
                            beginAtZero: true,
                            grid: { color: PALETTE.gridLine },
                            ticks: {
                                color: PALETTE.slate,
                                callback: (v) => v >= 1000 ? (v / 1000).toFixed(0) + "k" : v
                            },
                            title: { display: true, text: "Units Sold", color: PALETTE.slate, font: { size: 11 } }
                        },
                        y1: {
                            type: "linear",
                            position: "right",
                            beginAtZero: true,
                            grid: { drawOnChartArea: false },
                            ticks: {
                                color: PALETTE.slate,
                                callback: (v) => "$" + (v >= 1000 ? (v / 1000).toFixed(0) + "k" : v)
                            },
                            title: { display: true, text: "Calculated Revenue ($)", color: PALETTE.slate, font: { size: 11 } }
                        }
                    }
                }
            });
        } catch (err) {
            setLoading("store-sales-wrap", false);
            console.error("Error loading store sales:", err);
        }
    }

    // ==========================================================
    // 8. CHART: PRODUCT MOVEMENT (Fast / Normal / Slow)
    // ==========================================================
    async function loadMovementSummary() {
        const canvas = document.getElementById("chart-movement-summary");
        if (!canvas) return;

        setLoading("movement-summary-wrap", true);
        const f = getActiveFilters();
        const url = `/api/dashboard/movement-summary?preset=${f.preset}&start_date=${f.start_date}&end_date=${f.end_date}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            setLoading("movement-summary-wrap", false);
            destroyChart("movementSummary");

            const ctx = canvas.getContext("2d");
            charts.movementSummary = new Chart(ctx, {
                type: "doughnut",
                data: {
                    labels: data.labels,
                    datasets: [{
                        data: data.counts,
                        backgroundColor: [PALETTE.emerald, PALETTE.primary, PALETTE.amber],
                        borderWidth: 2,
                        borderColor: "#ffffff"
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            position: "bottom",
                            labels: { boxWidth: 12, font: { size: 11 }, padding: 12 }
                        },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => {
                                    const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
                                    const val = ctx.raw;
                                    const pct = total > 0 ? ((val / total) * 100).toFixed(1) : 0;
                                    return ` ${ctx.label}: ${val} products (${pct}%)`;
                                }
                            }
                        }
                    },
                    cutout: "62%"
                }
            });
        } catch (err) {
            setLoading("movement-summary-wrap", false);
            console.error("Error loading movement summary:", err);
        }
    }

    // ==========================================================
    // 9. CHART: RECOMMENDATION SIGNALS SUMMARY
    // ==========================================================
    async function loadRecommendationSummary() {
        const canvas = document.getElementById("chart-recommendation-summary");
        if (!canvas) return;

        setLoading("recommendation-summary-wrap", true);
        const f = getActiveFilters();
        const url = `/api/dashboard/recommendation-summary?preset=${f.preset}&start_date=${f.start_date}&end_date=${f.end_date}`;

        try {
            const res = await fetch(url);
            const data = await res.json();
            setLoading("recommendation-summary-wrap", false);
            destroyChart("recommendationSummary");

            const ctx = canvas.getContext("2d");
            charts.recommendationSummary = new Chart(ctx, {
                type: "bar",
                data: {
                    labels: data.labels,
                    datasets: [{
                        label: "Catalog Products",
                        data: data.counts,
                        backgroundColor: data.colors,
                        borderRadius: 4,
                        maxBarThickness: 24
                    }]
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: (ctx) => `${ctx.label}: ${ctx.parsed.x} products`
                            }
                        }
                    },
                    scales: {
                        x: {
                            beginAtZero: true,
                            ticks: { stepSize: 1, color: PALETTE.slate, font: { size: 11 } },
                            grid: { color: PALETTE.gridLine }
                        },
                        y: {
                            grid: { display: false },
                            ticks: { color: PALETTE.slate, font: { size: 10 } }
                        }
                    }
                }
            });
        } catch (err) {
            setLoading("recommendation-summary-wrap", false);
            console.error("Error loading recommendation summary:", err);
        }
    }

    // ==========================================================
    // MASTER REFRESH FUNCTION
    // ==========================================================
    function refreshAllCharts() {
        loadSalesTrend();
        loadRevenueTrend();
        loadCategorySales();
        loadTopProducts();
        loadInventoryStatus();
        loadInventoryCategories();
        loadStoreSales();
        loadMovementSummary();
        loadRecommendationSummary();
    }

    // ==========================================================
    // TOOLBAR EVENT LISTENERS
    // ==========================================================
    function setupFilterToolbar() {
        const isDashboard = document.getElementById("chart-sales-trend") || document.getElementById("filter-preset");
        if (!isDashboard) return;

        const presetEl = document.getElementById("filter-preset");
        const startEl = document.getElementById("filter-start-date");
        const endEl = document.getElementById("filter-end-date");
        const categoryEl = document.getElementById("filter-category");
        const storeEl = document.getElementById("filter-store");
        const applyBtn = document.getElementById("btn-apply-filters");
        const resetBtn = document.getElementById("btn-reset-filters");
        const storeLimitEl = document.getElementById("store-limit-select");

        // Presets date definitions from data attributes
        if (presetEl) {
            presetEl.addEventListener("change", function () {
                const opt = presetEl.options[presetEl.selectedIndex];
                const start = opt.getAttribute("data-start");
                const end = opt.getAttribute("data-end");
                if (start && end) {
                    if (startEl) startEl.value = start;
                    if (endEl) endEl.value = end;
                }
                refreshAllCharts();
            });
        }

        if (applyBtn) {
            applyBtn.addEventListener("click", function (e) {
                e.preventDefault();
                refreshAllCharts();
            });
        }

        if (resetBtn) {
            resetBtn.addEventListener("click", function (e) {
                e.preventDefault();
                if (presetEl) presetEl.value = "full";
                const fullOpt = presetEl ? presetEl.querySelector("option[value='full']") : null;
                if (fullOpt) {
                    if (startEl) startEl.value = fullOpt.getAttribute("data-start") || "2017-01-01";
                    if (endEl) endEl.value = fullOpt.getAttribute("data-end") || "2018-09-30";
                }
                if (categoryEl) categoryEl.value = "all";
                if (storeEl) storeEl.value = "all";
                refreshAllCharts();
            });
        }

        if (storeLimitEl) {
            storeLimitEl.addEventListener("change", function () {
                loadStoreSales();
            });
        }
    }

    // Initialize when DOM is ready
    document.addEventListener("DOMContentLoaded", function () {
        // Defensive guard: only execute dashboard logic when dashboard-specific DOM elements exist
        const isDashboard = document.getElementById("chart-sales-trend") || document.querySelector(".dashboard-metrics-grid") || document.getElementById("filter-preset");
        if (!isDashboard) {
            return;
        }
        setupFilterToolbar();
        refreshAllCharts();
    });

    // Expose functions globally for debugging/tests
    window.DashboardAnalytics = {
        loadSalesTrend,
        loadRevenueTrend,
        loadCategorySales,
        loadTopProducts,
        loadInventoryStatus,
        loadInventoryCategories,
        loadStoreSales,
        loadMovementSummary,
        loadRecommendationSummary,
        refreshAllCharts
    };
})();
