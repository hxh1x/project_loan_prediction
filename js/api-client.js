/**
 * Lendmark API Client
 * Replaces Supabase — talks to the local Python Flask server at http://localhost:5000
 */
var API_BASE = window.location.origin + "/api";

const api = {
  _token: localStorage.getItem("lm_token"),
  _user: JSON.parse(localStorage.getItem("lm_user") || "null"),

  _headers() {
    const h = { "Content-Type": "application/json" };
    if (this._token) h["Authorization"] = `Bearer ${this._token}`;
    return h;
  },

  async _request(method, path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: this._headers(),
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  },

  get: (path) => api._request("GET", path),
  post: (path, body) => api._request("POST", path, body),
  patch: (path, body) => api._request("PATCH", path, body),

  // ── Auth ──────────────────────────────────────────────
  async signUp(email, password, fullName) {
    return api.post("/auth/signup", { email, password, full_name: fullName });
  },

  async signIn(email, password) {
    const data = await api.post("/auth/login", { email, password });
    api._token = data.token;
    api._user = data.user;
    localStorage.setItem("lm_token", data.token);
    localStorage.setItem("lm_user", JSON.stringify(data.user));
    return data.user;
  },

  async signOut() {
    try { await api.post("/auth/logout"); } catch(_) {}
    api._token = null;
    api._user = null;
    localStorage.removeItem("lm_token");
    localStorage.removeItem("lm_user");
  },

  getStoredUser() {
    return api._user;
  },

  async verifySession() {
    if (!api._token) return null;
    try {
      const user = await api.get("/auth/me");
      api._user = user;
      localStorage.setItem("lm_user", JSON.stringify(user));
      return user;
    } catch(_) {
      api._token = null;
      api._user = null;
      localStorage.removeItem("lm_token");
      localStorage.removeItem("lm_user");
      return null;
    }
  },

  // ── Profiles ──────────────────────────────────────────
  getProfiles: () => api.get("/profiles"),
  getMyProfile: () => api.get("/profiles/me"),

  // ── Loan Applications ─────────────────────────────────
  getApplications: () => api.get("/loan-applications"),
  createApplication: (data) => api.post("/loan-applications", data),
  updateApplication: (id, data) => api.patch(`/loan-applications/${id}`, data),

  // ── Transactions ───────────────────────────────────────
  getTransactions: () => api.get("/transactions"),
  createTransaction: (data) => api.post("/transactions", data),

  // ── Stats ─────────────────────────────────────────────
  getManagerStats: () => api.get("/stats/manager"),
  getCustomerStats: () => api.get("/stats/customer"),
};

window.api = api;
