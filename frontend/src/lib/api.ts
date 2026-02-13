import axios from 'axios';
import { clerkClient } from '@clerk/clerk-react';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const apiClient = axios.create({
  baseURL: API_URL,
});

apiClient.interceptors.request.use(async (config) => {
  const session = await clerkClient.session.getActive();
  if (session) {
    config.headers.Authorization = `Bearer ${session.accessToken}`;
  }
  return config;
}, (error) => Promise.reject(error));

export default apiClient;
