import axios from "axios";

const apiUrl = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";
console.log(apiUrl)
const axiosInstance = axios.create({
  baseURL: apiUrl,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
});

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