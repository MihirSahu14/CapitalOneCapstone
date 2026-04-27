import axios from 'axios';

const baseURL = (process.env.REACT_APP_API_BASE_URL || '').trim();

const api = axios.create({
  baseURL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 15000
});

export function getApiErrorMessage(error, fallbackMessage = 'Request failed.') {
  if (error?.response?.data?.detail) {
    return error.response.data.detail;
  }

  if (typeof error?.response?.data?.message === 'string') {
    return error.response.data.message;
  }

  if (error?.message) {
    return error.message;
  }

  return fallbackMessage;
}

export default api;
