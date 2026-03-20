// ============================================================
// smart-home-app — Global JS + Alpine.js components
//
// Load order (all scripts carry `defer`, executed in DOM order):
//   1. htmx.min.js
//   2. app.js          ← this file (runs BEFORE Alpine)
//   3. alpine.min.js   ← fires alpine:init AFTER app.js has run
//   4. chart.umd.min.js
//   5. sortable.min.js
//
// Because app.js executes before alpine.min.js, the alpine:init
// listener below is guaranteed to be registered before Alpine fires
// it, and authFetch / getAccessToken are defined before any inline
// Alpine component calls them.
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
// Alpine.js component registrations.
// Wrapped in alpine:init so Alpine picks them up before it
// processes the DOM. Because app.js now loads before alpine.min.js
// (see defer order in base.html), this listener is always
// registered in time.
// ============================================================
document.addEventListener("alpine:init", () => {

    // --------------------------------------------------------
    // Device toggle component
    // --------------------------------------------------------
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

    // --------------------------------------------------------
    // Modal component
    // --------------------------------------------------------
    Alpine.data("modal", () => ({
        open: false,
        show() { this.open = true; },
        hide() { this.open = false; },
    }));

    // --------------------------------------------------------
    // Temperature control component
    // --------------------------------------------------------
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

    // --------------------------------------------------------
    // Brightness control component
    // --------------------------------------------------------
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

}); // end alpine:init

// ============================================================
// Auth gate — redirect to /login if no token is set.
// ============================================================
function _checkAuth() {
    const path = window.location.pathname;
    const publicPaths = ["/login"];
    if (!publicPaths.includes(path) && !getAccessToken()) {
        window.location.href = "/login?next=" + encodeURIComponent(path);
    }
}

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
//   1. Re-check auth (token may have expired during the session).
//   2. Re-initialise Alpine on the swapped <main> content.
//
//   WHY destroyTree + initTree (not just initTree):
//   When HTMX replaces the body innerHTML, Alpine's MutationObserver fires
//   immediately — BEFORE HTMX re-executes the inline <script> tags from
//   {% block scripts %} (e.g. schedulesPage, groupManager, dashboardPage).
//   Alpine tries to init x-data="schedulesPage()" but the function is not
//   yet defined, so it either throws silently or partially initialises the
//   element (setting _x_dataStack). A subsequent plain initTree() call then
//   SKIPS that element (already has _x_dataStack), leaving the component in
//   a broken, data-empty state — which is exactly what the user sees.
//   destroyTree() clears all Alpine state on <main> first; initTree() then
//   does a clean initialisation — at this point HTMX has already executed
//   all inline scripts, so every page function is defined and ready.
//   The <html> x-data (sidebarOpen) and the sidebar are outside <main> and
//   are therefore unaffected by destroyTree.
document.addEventListener("htmx:afterSettle", () => {
    _checkAuth();
    if (!window.Alpine) return;
    const main = document.querySelector("main");
    if (main) {
        Alpine.destroyTree(main);
        Alpine.initTree(main);
    }
});
