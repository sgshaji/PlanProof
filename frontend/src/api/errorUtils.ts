import axios from 'axios';

const DEFAULT_TIMEOUT_MESSAGE =
  'Request timed out. Please check your connection and try again.';
const DEFAULT_NETWORK_MESSAGE =
  'Unable to reach the server. This may be a network issue or a CORS configuration problem.';

export const getApiErrorMessage = (error: unknown, fallback: string) => {
  if (axios.isAxiosError(error)) {
    if (
      error.code === 'ECONNABORTED' ||
      error.message?.toLowerCase().includes('timeout')
    ) {
      return DEFAULT_TIMEOUT_MESSAGE;
    }

    if (error.code === 'ERR_NETWORK' || error.message === 'Network Error') {
      return DEFAULT_NETWORK_MESSAGE;
    }

    const status = error.response?.status;
    if (status && status >= 500) {
      return `Server error (${status}). Please try again later.`;
    }

    return (
      (error.response?.data as { detail?: string })?.detail ||
      error.message ||
      fallback
    );
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
};
