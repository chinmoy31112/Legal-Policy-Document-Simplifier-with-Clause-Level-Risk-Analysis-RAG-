import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { API_BASE_URL } from './constants';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
});

apiClient.interceptors.request.use((config) => {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Refresh token queue to avoid multiple simultaneous refresh requests
let isRefreshing = false;
let failedQueue: Array<{
  resolve: (token: string) => void;
  reject: (error: unknown) => void;
}> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error);
    } else if (token) {
      prom.resolve(token);
    }
  });
  failedQueue = [];
};

// Response interceptor with automatic silent token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;

    // If there is no response or error is not 401, reject immediately
    if (!error.response || error.response.status !== 401 || !originalRequest) {
      return Promise.reject(error);
    }

    // Do NOT intercept auth endpoints (login, register, refresh) to avoid infinite redirect loops
    const requestUrl = originalRequest.url || '';
    if (
      requestUrl.includes('/auth/login') ||
      requestUrl.includes('/auth/register') ||
      requestUrl.includes('/auth/refresh')
    ) {
      return Promise.reject(error);
    }

    if (typeof window === 'undefined') {
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem('refresh_token');

    // If there is no refresh token, clear storage and redirect to login
    if (!refreshToken) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      if (window.location.pathname !== '/login') {
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }

    // If already retried this request, clear tokens and redirect
    if (originalRequest._retry) {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      if (window.location.pathname !== '/login') {
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.href = '/login';
      }
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    // If another request is currently refreshing the token, wait for it
    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((newToken) => {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return apiClient(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    isRefreshing = true;

    try {
      // Call refresh endpoint with a clean axios instance (to bypass interceptors)
      const refreshResponse = await axios.post(`${API_BASE_URL}/auth/refresh`, {
        refresh_token: refreshToken,
      });

      const newTokens = refreshResponse.data?.data;
      if (!newTokens?.access_token) {
        throw new Error('Refresh response missing access token');
      }

      localStorage.setItem('access_token', newTokens.access_token);
      if (newTokens.refresh_token) {
        localStorage.setItem('refresh_token', newTokens.refresh_token);
      }

      apiClient.defaults.headers.common.Authorization = `Bearer ${newTokens.access_token}`;
      originalRequest.headers.Authorization = `Bearer ${newTokens.access_token}`;

      processQueue(null, newTokens.access_token);

      return apiClient(originalRequest);
    } catch (refreshError) {
      processQueue(refreshError, null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      if (window.location.pathname !== '/login') {
        // eslint-disable-next-line @next/next/no-location-assign-relative-destination
        window.location.href = '/login';
      }
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);

export default apiClient;
