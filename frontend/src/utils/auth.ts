export const isAuthBypassed = (): boolean => {
  if (import.meta.env.VITE_AUTH_BYPASS === 'true') {
    return true;
  }

  if (typeof window === 'undefined') {
    return false;
  }

  return window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
};
