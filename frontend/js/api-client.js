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
  delete: (path) => api._request("DELETE", path),

  // ── Auth ──────────────────────────────────────────────
  async signUp(data) {
    // If first arg is an object, use it directly, otherwise build object from args (legacy support)
    const payload = (typeof data === 'object') ? data : { 
      email: arguments[0], 
      password: arguments[1], 
      full_name: arguments[2] 
    };
    return api.post("/auth/signup", payload);
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
  updateProfile: (data) => api.post("/auth/profile", data),
  async uploadProfilePhoto(file) {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/auth/profile-photo`, {
      method: "POST",
      headers: { "Authorization": `Bearer ${this._token}` },
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Upload failed");
    return data;
  },

  // ── Users ─────────────────────────────────────────────
  updateUserStatus: (id, status) => api.patch(`/users/${id}/status`, { status }),

  // ── Loan Applications ─────────────────────────────────
  getApplications: () => api.get("/loan-applications"),
  createApplication: (data) => api.post("/loan-applications", data),
  updateApplication: (id, data) => api.patch(`/loan-applications/${id}`, data),

  // ── Transactions ───────────────────────────────────────
  getTransactions: () => api.get("/transactions"),
  createTransaction: (data) => api.post("/transactions", data),

  // ── Stats ─────────────────────────────────────────────
  getManagerStats: () => api.get("/stats/manager"),
  getManagerChartData: () => api.get("/stats/manager/charts"),
  getManagerCustomerDetails: (id) => api.get("/manager/customer/" + id),
  getCustomerStats: () => api.get("/stats/customer"),

  // ── ML Prediction (Random Forest) ────────────────────
  predictLoan: (data) => api.post("/predict", data),
  getModelMeta: () => api.get("/ml/meta"),

  // ── EMI Management ─────────────────────────────────
  processEmis: () => api.post("/emi/process"),
  getEmiSchedules: () => api.get("/emi/schedules"),
  getEmiSettings: (loanId) => api.get("/emi/settings/" + loanId),
  updateEmiSettings: (loanId, data) => api.post("/emi/settings/" + loanId, data),
  payEmi: (emiId, data) => api.post("/emi/pay/" + emiId, data),
  getEmiSummary: () => api.get("/emi/summary"),
  getEmiHealthScore: () => api.get("/emi/health-score"),
  requestReschedule: (loanId, emi_day) => api.post("/emi/reschedule/" + loanId, { emi_day }),
  getEmiOverdue: () => api.get("/emi/overdue"),

  // ── Notifications ──────────────────────────────────
  getNotifications: () => api.get("/notifications"),
  markNotificationRead: (id) => api.post("/notifications/" + id + "/read"),
  markAllRead: () => api.post("/notifications/read-all"),
  getUnreadCount: () => api.get("/notifications/unread-count"),
  deleteNotification: (id) => api.delete("/notifications/" + id),
};

window.api = api;
