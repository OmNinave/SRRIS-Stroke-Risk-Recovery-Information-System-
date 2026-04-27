// SRRIS Frontend Configuration
// Centralized API endpoints for better portability

const IS_PROD = process.env.NODE_ENV === 'production';

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const ENDPOINTS = {
  AUTH: `${API_BASE_URL}/api/v1/auth`,
  PATIENTS: `${API_BASE_URL}/api/v1/patients`,
  ANALYTICS: `${API_BASE_URL}/api/v1/analytics`,
  RADIOLOGY: `${API_BASE_URL}/api/v1/radiology`,
};
