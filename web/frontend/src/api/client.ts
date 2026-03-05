/** Axios client with JWT interceptor. */
import axios from "axios";

const api = axios.create({
  baseURL: "/api/v1",
  withCredentials: true,
  headers: { "Content-Type": "application/json" },
});

// Auto-refresh on 401 (skip for auth endpoints to avoid loops)
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config;
    const isAuthEndpoint = original?.url?.startsWith("/auth/");
    if (err.response?.status === 401 && !original._retry && !isAuthEndpoint) {
      original._retry = true;
      try {
        await axios.post("/api/v1/auth/refresh", {}, { withCredentials: true });
        return api(original);
      } catch {
        // Let the AuthContext handle the unauthenticated state
        return Promise.reject(err);
      }
    }
    return Promise.reject(err);
  },
);

export default api;
