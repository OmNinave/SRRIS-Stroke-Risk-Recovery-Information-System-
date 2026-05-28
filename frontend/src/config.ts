// SRRIS Frontend Configuration
// API calls are routed through Next.js rewrites in next.config.ts
// which proxies /api/* -> http://127.0.0.1:8080/api/*
// Set NEXT_PUBLIC_API_URL in your .env.local to override for production.

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

export const ENDPOINTS = {
  AUTH: `${API_BASE_URL}/api/v1/auth`,
  PATIENTS: `${API_BASE_URL}/api/v1/patients`,
  ANALYTICS: `${API_BASE_URL}/api/v1/analytics`,
  RADIOLOGY: `${API_BASE_URL}/api/v1/radiology`,
};
