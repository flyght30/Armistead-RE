import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: `${API_URL}/api`,
});

/**
 * Hook to set up auth interceptor.
 * Call once at app level or in a provider.
 */
export function setupAuthInterceptor(getToken: () => Promise<string | null>) {
  apiClient.interceptors.request.use(
    async (config) => {
      try {
        const token = await getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      } catch {
        // If auth fails, send request without token
      }
      return config;
    },
    (error) => Promise.reject(error),
  );
}

export default apiClient;
