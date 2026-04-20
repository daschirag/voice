import axios from "axios";
const api = axios.create({ baseURL: "/api/v1", timeout: 300000 });
export const analyzeAudio = (file, role) => {
  const form = new FormData();
  form.append("file", file);
  form.append("role", role);
  return api.post("/analyze", form);
};
export const getStatus  = (id) => api.get("/status/" + id);
export const getReport  = (id) => api.get("/report/" + id);
export const getPdfUrl  = (id) => "/api/v1/report/" + id + "/pdf";
export const getHtmlUrl = (id) => "/reports/" + id + "_report.html";