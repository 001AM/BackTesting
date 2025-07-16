import axios from "axios";

// Create an Axios instance with base configuration
const axiosInstance = axios.create({
  baseURL: `http://localhost:8000/api/v1`,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
    "Accept": "application/json",
  },
});


// Request Interceptor (Fixed to handle token and project correctly)
axiosInstance.interceptors.request.use(
  (config) => {
    // Fixed: Use AND (&&) instead of OR (||) for excluding auth endpoints
    if (!config.url.includes('/register/') && !config.url.includes('/login/')) {
      const token =
        typeof window !== "undefined" ? localStorage.getItem("access-token") : null;

      if (token) {
        config.headers["Authorization"] = `Bearer ${token}`;
      }
      
    }

    // Log request details for debugging
    console.log("Request Config:", {
      url: config.url,
      method: config.method,
      headers: config.headers,
      data: config.data
    });

    return config;
  },
  (error) => {
    console.log("Request Interceptor Error:", error);
    return Promise.reject(error);
  }
);

// Response Interceptor (Enhanced error logging)
axiosInstance.interceptors.response.use(
  (response) => {
    console.log("Response:", {
      status: response.status,
      data: response.data
    });
    return response;
  },
  async (error) => {
    console.log("Full Axios Error:", {
      message: error.message,
      code: error.code,
      response: error.response ? {
        status: error.response.status,
        data: error.response.data,
        headers: error.response.headers
      } : 'No response',
      request: error.request ? 'Request exists' : 'No request',
    });

    const originalRequest = error.config;

    // Handle token refresh for 401 errors
    // if (error.response?.status === 401 && !originalRequest._retry) {
    //   originalRequest._retry = true;
    //   try {
    //     const newToken = await refreshToken();

    //     if (typeof window !== "undefined") {
    //       localStorage.setItem("access-token", newToken);
    //     }

    //     originalRequest.headers["Authorization"] = `Bearer ${newToken}`;
    //     return axiosInstance(originalRequest);
    //   } catch (refreshError) {
    //     if (typeof window !== "undefined") {
    //       localStorage.removeItem("access-token");
    //       localStorage.removeItem("refresh-token");
    //       window.location.href = "/login";
    //     }
    //     return Promise.reject(refreshError);
    //   }
    // }

    return Promise.reject(error);
  }
);

// Utility function for token refresh (with full URL)
async function refreshToken() {
  try {
    const response = await axios.post(
      `${import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000"}/api/refresh-token`,
      {
        refreshToken: localStorage.getItem("refresh-token"),
      }
    );
    return response.data.accessToken;
  } catch (error) {
    console.log("Token Refresh Error:", error);
    throw error;
  }
}

// Enhanced error handler
export function handleApiError(error) {
  console.log("API Error Details:", error);

  if (axios.isAxiosError(error)) {
    if (error?.response) {
      console.log("Detailed Error Response:", {
        data: error?.response.data,
        status: error?.response.status,
        headers: error?.response.headers
      });

      switch (error.response.status) {
        case 400:
          return error.response.data.detail ||
            error.response.data.message ||
            "Bad Request: Please check your input.";
        case 401:
          return "Unauthorized: Please log in again.";
        case 403:
          return "Forbidden: You do not have permission.";
        case 404:
          return "Not Found: The requested resource does not exist.";
        case 500:
          return "Server Error: Please try again later.";
        default:
          return error.response.data.message || "An unexpected error occurred.";
      }
    } else if (error.request) {
      return "No response received from server. Please check your network.";
    } else {
      return "Error setting up the request.";
    }
  }
  return "An unexpected error occurred.";
}

// Export utility functions
export const api = {
  get: (url, config = {}) => axiosInstance.get(url, config),
  post: async (url, data = {}, config = {}) => {
    try {
      console.log("Data", url, data)
      return await axiosInstance.post(url, data, config);
    } catch (error) {
      throw error;
    }
  },
  put: (url, data = {}, config = {}) => axiosInstance.put(url, data, config),
  delete: (url, config = {}) => axiosInstance.delete(url, config),
  patch: (url, data = {}, config = {}) => axiosInstance.patch(url, data, config),
};

export default axiosInstance;