/**
 * Smart Inventory & Sales Analysis System - Enterprise Shell & Interaction Script
 * Manages responsive navigation rail, drawer overlay, and user profile dropdown.
 */

document.addEventListener("DOMContentLoaded", () => {
    const body = document.body;
    const sidebar = document.getElementById("appSidebar");
    const mobileOverlay = document.getElementById("mobileOverlay");
    const sidebarMenuBtn = document.getElementById("sidebarMenuBtn");
    const sidebarToggleInner = document.getElementById("sidebarToggleInner");
    const userMenuContainer = document.getElementById("userMenuContainer");
    const userMenuBtn = document.getElementById("userMenuBtn");

    // =========================================================================
    // 1. SIDEBAR COLLAPSE / EXPAND PERSISTENCE (DESKTOP)
    // =========================================================================
    const STORAGE_KEY = "smart_inventory_sidebar_expanded";
    const isDesktop = () => window.innerWidth >= 992;

    // URL parameter overrides for headless QA validation and deep-linking
    const urlParams = new URLSearchParams(window.location.search);
    const paramSidebar = urlParams.get("sidebar");
    const paramMobileNav = urlParams.get("mobile_nav");

    if (paramSidebar === "expanded") {
        body.classList.remove("sidebar-collapsed");
        body.classList.add("sidebar-expanded");
        localStorage.setItem(STORAGE_KEY, "true");
    } else if (paramSidebar === "collapsed") {
        body.classList.remove("sidebar-expanded");
        body.classList.add("sidebar-collapsed");
        localStorage.setItem(STORAGE_KEY, "false");
    } else {
        const savedState = localStorage.getItem(STORAGE_KEY);
        if (isDesktop() && savedState === "true") {
            body.classList.remove("sidebar-collapsed");
            body.classList.add("sidebar-expanded");
        } else if (isDesktop()) {
            body.classList.remove("sidebar-expanded");
            body.classList.add("sidebar-collapsed");
        }
    }

    function toggleDesktopSidebar() {
        if (body.classList.contains("sidebar-expanded")) {
            body.classList.remove("sidebar-expanded");
            body.classList.add("sidebar-collapsed");
            localStorage.setItem(STORAGE_KEY, "false");
        } else {
            body.classList.remove("sidebar-collapsed");
            body.classList.add("sidebar-expanded");
            localStorage.setItem(STORAGE_KEY, "true");
        }
    }

    // =========================================================================
    // 2. MOBILE DRAWER NAVIGATION
    // =========================================================================
    function openMobileDrawer() {
        body.classList.add("mobile-drawer-open");
        if (sidebar) sidebar.classList.add("open");
        if (mobileOverlay) mobileOverlay.classList.add("active");
    }

    function closeMobileDrawer() {
        body.classList.remove("mobile-drawer-open");
        if (sidebar) sidebar.classList.remove("open");
        if (mobileOverlay) mobileOverlay.classList.remove("active");
    }

    // Unified toggle handler for the top-bar button
    if (!isDesktop() && (paramMobileNav === "open" || localStorage.getItem("smart_inventory_mobile_open") === "true")) {
        openMobileDrawer();
    }
    if (sidebarMenuBtn) {
        sidebarMenuBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            if (isDesktop()) {
                toggleDesktopSidebar();
            } else {
                if (body.classList.contains("mobile-drawer-open")) {
                    closeMobileDrawer();
                } else {
                    openMobileDrawer();
                }
            }
        });
    }

    // Inner toggle button inside sidebar header
    if (sidebarToggleInner) {
        sidebarToggleInner.addEventListener("click", (e) => {
            e.stopPropagation();
            if (isDesktop()) {
                toggleDesktopSidebar();
            } else {
                closeMobileDrawer();
            }
        });
    }

    // Backdrop click closes mobile drawer
    if (mobileOverlay) {
        mobileOverlay.addEventListener("click", () => {
            closeMobileDrawer();
        });
    }

    // Close mobile drawer when clicking any nav link
    if (sidebar) {
        const navLinks = sidebar.querySelectorAll(".nav-link");
        navLinks.forEach((link) => {
            link.addEventListener("click", () => {
                if (!isDesktop()) {
                    closeMobileDrawer();
                }
            });
        });
    }

    // Handle window resize events gracefully
    window.addEventListener("resize", () => {
        if (isDesktop()) {
            closeMobileDrawer();
            const currentSaved = localStorage.getItem(STORAGE_KEY);
            if (currentSaved === "true") {
                body.classList.remove("sidebar-collapsed");
                body.classList.add("sidebar-expanded");
            } else {
                body.classList.remove("sidebar-expanded");
                body.classList.add("sidebar-collapsed");
            }
        }
    });

    // =========================================================================
    // 3. USER PROFILE DROPDOWN MENU
    // =========================================================================
    if (userMenuBtn && userMenuContainer) {
        userMenuBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            const isOpen = userMenuContainer.classList.contains("open");
            if (isOpen) {
                userMenuContainer.classList.remove("open");
                userMenuBtn.setAttribute("aria-expanded", "false");
            } else {
                userMenuContainer.classList.add("open");
                userMenuBtn.setAttribute("aria-expanded", "true");
            }
        });

        // Close dropdown when clicking outside
        document.addEventListener("click", (e) => {
            if (!userMenuContainer.contains(e.target)) {
                userMenuContainer.classList.remove("open");
                userMenuBtn.setAttribute("aria-expanded", "false");
            }
        });

        // Close dropdown on Escape key
        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape") {
                if (userMenuContainer.classList.contains("open")) {
                    userMenuContainer.classList.remove("open");
                    userMenuBtn.setAttribute("aria-expanded", "false");
                    userMenuBtn.focus();
                }
                if (!isDesktop() && body.classList.contains("mobile-drawer-open")) {
                    closeMobileDrawer();
                }
            }
        });
    }
});
