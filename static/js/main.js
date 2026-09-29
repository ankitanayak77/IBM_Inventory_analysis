/**
 * Smart Inventory & Sales Analysis System - Main Client Script
 * Phase 4: UI interactions and responsive drawer handling.
 */

document.addEventListener("DOMContentLoaded", () => {
    // Mobile Drawer Toggle
    const mobileBtn = document.getElementById("mobileMenuBtn");
    const sidebar = document.getElementById("appSidebar");
    const overlay = document.getElementById("mobileOverlay");

    if (mobileBtn && sidebar) {
        mobileBtn.addEventListener("click", () => {
            sidebar.classList.toggle("open");
            if (overlay) overlay.classList.toggle("active");
        });
    }

    if (overlay && sidebar) {
        overlay.addEventListener("click", () => {
            sidebar.classList.remove("open");
            overlay.classList.remove("active");
        });
    }
});
