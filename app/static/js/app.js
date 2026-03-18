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
document.addEventListener("DOMContentLoaded", () => {
    const path = window.location.pathname;
    const publicPaths = ["/login"];

    if (!publicPaths.includes(path) && !getAccessToken()) {
        window.location.href = "/login?next=" + encodeURIComponent(path);
        return;
    }

    // Add Authorization header to all HTMX requests
    document.body.addEventListener("htmx:configRequest", (event) => {
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
    document.body.addEventListener("htmx:responseError", (event) => {
        if (event.detail.xhr?.status === 401) {
            localStorage.removeItem("access_token");
            window.location.href = "/login?next=" + encodeURIComponent(window.location.pathname);
        }
    });

    // Loading indicator
    document.body.addEventListener("htmx:beforeRequest", () => {
        document.getElementById("loading-indicator")?.classList.remove("hidden");
    });
    document.body.addEventListener("htmx:afterRequest", () => {
        document.getElementById("loading-indicator")?.classList.add("hidden");
    });
});

// ============================================================
// Alpine.js: Device toggle component
// ============================================================
document.addEventListener("alpine:init", () => {
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
    // Alpine.js: Modal component
    // ============================================================
    Alpine.data("modal", () => ({
        open: false,
        show() { this.open = true; },
        hide() { this.open = false; },
    }));

    // ============================================================
    // Alpine.js: Temperature control component
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
});
