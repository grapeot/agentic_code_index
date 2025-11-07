// API utility for making requests that work with base path
// When deployed at /service-name, API calls should go to /service-name/api/...

// Get base path from Vite's import.meta.env.BASE_URL
// BASE_URL is set by Vite based on the base config (e.g., '/service-name/')
const BASE_URL = import.meta.env.BASE_URL || '/'

// Helper function to build API URL
export function apiUrl(path) {
  // Remove leading slash if present
  const cleanPath = path.startsWith('/') ? path.slice(1) : path
  // Ensure path starts with 'api/'
  const apiPath = cleanPath.startsWith('api/') ? cleanPath : `api/${cleanPath}`
  // Combine base URL with API path
  // BASE_URL already ends with '/', so we don't need to add another one
  return `${BASE_URL}${apiPath}`
}

// Wrapper for fetch that uses apiUrl
export async function apiFetch(path, options) {
  return fetch(apiUrl(path), options)
}

