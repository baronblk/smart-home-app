// ============================================================
// smart-home-app — Global JS + Alpine.js components
// ============================================================

// ============================================================
// Auth helper — retrieves the access token from localStorage.
// ============================================================
function getAccessToken() {
    return localStorage.getItem("access_token") || "";
}

/**
 * Authenticated fetch wrapper — automatically adds Authorization header
 * and redirects to /login on 401.
 */
async function authFetch(url, options = {}) {
    const token = getAccessToken();
    const headers = {
        ...options.headers,
        "Authorization": `Bearer ${token}`,
    };
    const resp = await fetch(url, { ...options, headers });
    if (resp.status === 401) {
        // Token expired or invalid — redirect to login
        localStorage.removeItem("access_token");
        window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
        return resp;
    }
    return resp;
}

// ============================================================
// Auth gate — redirect to /login if no token is set.
// Excluded pages: /login
// ============================================================
function _checkAuth() {
    const path = window.location.pathname;
    const publicPaths = ["/login"];
    if (!publicPaths.includes(path) && !getAccessToken()) {
        window.location.href = "/login?next=" + encodeURIComponent(path);
    }
}

// Initial page load
document.addEventListener("DOMContentLoaded", _checkAuth);

// ============================================================
// HTMX global event listeners — attached to document so they
// survive hx-boost navigation (body innerHTML is replaced but
// the document object is permanent).
// ============================================================

// Add Authorization header to all HTMX requests
document.addEventListener("htmx:configRequest", (event) => {
    const token = getAccessToken();
    if (token) {
        event.detail.headers["Authorization"] = `Bearer ${token}`;
    }
    // CSRF token support (future)
    const csrfToken = document
        .querySelector('meta[name="csrf-token"]')
        ?.getAttribute("content");
    if (csrfToken) {
        event.detail.headers["X-CSRF-Token"] = csrfToken;
    }
});

// Handle 401 responses from HTMX
document.addEventListener("htmx:responseError", (event) => {
    if (event.detail.xhr?.status === 401) {
        localStorage.removeItem("access_token");
        window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
    }
});

// Loading indicator
document.addEventListener("htmx:beforeRequest", () => {
    document.getElementById("loading-indicator")?.classList.remove("hidden");
});
document.addEventListener("htmx:afterRequest", () => {
    document.getElementById("loading-indicator")?.classList.add("hidden");
});

// After every hx-boost navigation:
//  1. Re-check auth (token may have been removed)
//  2. Re-initialise Alpine on the new body content.
//     Inline functions defined in {% block scripts %} are guaranteed
//     to be executed before htmx:afterSettle fires. Alpine.data()
//     components are already in the registry. initTree() skips
//     elements that Alpine already owns (_x_dataStack present) and
//     retries any that failed during the initial swap (race between
//     MutationObserver and inline script execution).
document.addEventListener("htmx:afterSettle", () => {
    _checkAuth();
    if (window.Alpine) {
        Alpine.initTree(document.body);
    }
});

// ============================================================
// Alpine.js components — registered directly (NOT inside an
// alpine:init listener).
//
// Reason: both alpine.min.js and app.js carry the `defer`
// attribute. Deferred scripts execute in DOM order, so Alpine
// always runs before app.js. By the time app.js executes,
// Alpine has already fired alpine:init and started processing
// the DOM — any alpine:init listener registered here would
// never be called.
//
// Calling Alpine.data() after Alpine.start() is fully supported
// by Alpine 3.x: newly registered components are picked up by
// Alpine's MutationObserver for all HTMX-swapped content.
// The Alpine.initTree() call at the bottom of this file handles
// the initial page load for elements that Alpine tried (and
// failed) to initialise before these registrations existed.
// ============================================================

// ============================================================
// Device toggle component
// ============================================================
Alpine.data("deviceToggle", (ain, initialState) => ({
    ain,
    isOn: initialState,
    loading: false,

    async toggle() {
        this.loading = true;
        const action = this.isOn ? "off" : "on";
        try {
            const resp = await authFetch(`/api/v1/devices/${this.ain}/${action}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
            });
            if (resp.ok) {
                this.isOn = !this.isOn;
            } else {
                console.error("Toggle failed:", resp.status);
            }
        } catch (err) {
            console.error("Toggle error:", err);
        } finally {
            this.loading = false;
        }
    },
}));

// ============================================================
// Modal component
// ============================================================
Alpine.data("modal", () => ({
    open: false,
    show() { this.open = true; },
    hide() { this.open = false; },
}));

// ============================================================
// Temperature control component
// ============================================================
Alpine.data("tempControl", (ain, currentTemp) => ({
    ain,
    temperature: currentTemp,
    saving: false,

    async setTemperature() {
        this.saving = true;
        try {
            await authFetch(`/api/v1/devices/${this.ain}/temperature`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ celsius: this.temperature }),
            });
        } finally {
            this.saving = false;
        }
    },
}));

// ============================================================
// Brightness control component
// ============================================================
Alpine.data("brightnessControl", (ain, currentLevel) => ({
    ain,
    level: currentLevel,
    saving: false,

    async setBrightness() {
        this.saving = true;
        try {
            await authFetch(`/api/v1/devices/${this.ain}/brightness`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ level: this.level }),
            });
        } finally {
            this.saving = false;
        }
    },
}));

// ============================================================
// Re-initialise any x-data elements that Alpine attempted to
// process before these Alpine.data() registrations existed
// (app.js runs after alpine.min.js due to defer ordering).
// Already-initialised elements are skipped automatically.
// ============================================================
Alpine.initTree(document.body);
