import { MutationCache, QueryCache, QueryClient } from '@tanstack/react-query';
import { ApiError } from './types/apiError';

function handleGlobalError(error: unknown) {
  if (error instanceof ApiError && error.status === 401) {
    const clear = (window as unknown as { __authClearSession?: () => void }).__authClearSession;
    clear?.();
    if (window.location.pathname !== '/login') {
      window.location.href = '/login';
    }
  }
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError && (error.status === 401 || error.status === 403 || error.status === 404)) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
  queryCache: new QueryCache({ onError: handleGlobalError }),
  mutationCache: new MutationCache({ onError: handleGlobalError }),
});
