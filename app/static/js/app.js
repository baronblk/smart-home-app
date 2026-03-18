// ============================================================
// smart-home-app — Alpine.js component definitions
// ============================================================

// Global HTMX configuration
document.addEventListener("DOMContentLoaded", () => {
    // Add CSRF token to all HTMX requests (Phase 2+)
    document.body.addEventListener("htmx:configRequest", (event) => {
        const token = document
            .querySelector('meta[name="csrf-token"]')
            ?.getAttribute("content");
        if (token) {
            event.detail.headers["X-CSRF-Token"] = token;
        }
    });

    // Show loading indicator on HTMX requests
    document.body.addEventListener("htmx:beforeRequest", () => {
        document.getElementById("loading-indicator")?.classList.remove("hidden");
    });

    document.body.addEventListener("htmx:afterRequest", () => {
        document.getElementById("loading-indicator")?.classList.add("hidden");
    });
});

// ============================================================
// Alpine.js: Device toggle component
// Used in device cards to toggle switch state via HTMX.
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
                const resp = await fetch(`/api/v1/devices/${this.ain}/${action}`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${getAccessToken()}`,
                    },
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
                await fetch(`/api/v1/devices/${this.ain}/temperature`, {
                    method: "PUT",
                    headers: {
                        "Content-Type": "application/json",
                        "Authorization": `Bearer ${getAccessToken()}`,
                    },
                    body: JSON.stringify({ celsius: this.temperature }),
                });
            } finally {
                this.saving = false;
            }
        },
    }));
});

// ============================================================
// Auth helper — retrieves the access token from localStorage.
// Phase 2+ will populate this via the login flow.
// ============================================================
function getAccessToken() {
    return localStorage.getItem("access_token") || "";
}
