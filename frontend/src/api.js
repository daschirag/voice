import axios from "axios";

const BACKEND = "https://protract-bless-variable.ngrok-free.dev";

const api = axios.create({
  baseURL: BACKEND + "/api/v1",
  timeout: 300000,
  headers: {
    "ngrok-skip-browser-warning": "true",
  }
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  config.headers["ngrok-skip-browser-warning"] = "true";
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.clear();
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

export const authAPI = {
  register: (data) => api.post("/auth/register", data, {
    headers: { "Content-Type": "multipart/form-data", "ngrok-skip-browser-warning": "true" }
  }),
  login: (username, password) => {
    const form = new FormData();
    form.append("username", username);
    form.append("password", password);
    return api.post("/auth/login", form);
  },
  me: () => api.get("/auth/me"),
};

export const clientAPI = {
  analyze: (file, role) => {
    const form = new FormData();
    form.append("file", file);
    form.append("role", role);
    return api.post("/analyze", form);
  },
  myReports: () => api.get("/my-reports"),
  getReport: (id) => api.get(`/report/${id}`),
  downloadPdf: async (id, filename) => {
    const response = await api.get(`/report/${id}/pdf`, {
      responseType: "blob",
      headers: { "ngrok-skip-browser-warning": "true" }
    });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename || `speech_report_${id}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  getPdfUrl: (id) => BACKEND + `/api/v1/report/${id}/pdf`,
  getHtmlUrl: (id) => BACKEND + `/reports/${id}_report.html`,
};

export const adminAPI = {
  getUsers: () => api.get("/admin/users"),
  verifyUser: (id) => api.put(`/admin/verify/${id}`),
  unverifyUser: (id) => api.put(`/admin/unverify/${id}`),
  deleteUser: (id) => api.delete(`/admin/users/${id}`),
  getReports: (params) => api.get("/admin/reports", { params }),
  getStats: () => api.get("/admin/stats"),
  downloadPdf: async (id, filename) => {
    const response = await api.get(`/report/${id}/pdf`, {
      responseType: "blob",
      headers: { "ngrok-skip-browser-warning": "true" }
    });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: "application/pdf" }));
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename || `speech_report_${id}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  getPdfUrl: (id) => BACKEND + `/api/v1/report/${id}/pdf`,
};

export default api;