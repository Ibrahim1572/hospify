import axios from 'axios';

const api = axios.create({
  // baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api',
  baseURL: '/api',
  withCredentials: true, // Important for sending/receiving cookies (JWTs)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor to handle token refresh if implemented, or redirect to login
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If error is 401 and we haven't already retried
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;
      
      try {
        // Attempt to refresh the token using the refresh cookie
        await axios.post(
          // `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'}/auth/refresh`,
          '/api/auth/refresh',
          {},
          { withCredentials: true }
        );
        
        // If successful, retry the original request
        return api(originalRequest);
      } catch (refreshError) {
        // If refresh fails, redirect to login
        // Let the AuthContext handle the actual redirect and state cleanup
        console.error("Session expired, please login again");
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export default api;
