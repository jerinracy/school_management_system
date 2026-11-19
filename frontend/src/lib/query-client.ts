import { QueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError } from "@/lib/errors";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      staleTime: 60 * 1000, // 1 minute
      retry: (failureCount, error) => {
        if (error instanceof ApiError) {
          // Never retry 4xx errors
          if (error.status >= 400 && error.status < 500) {
            return false;
          }
        }
        return failureCount < 2;
      },
    },
    mutations: {
      retry: false,
      onError: (error) => {
        if (error instanceof ApiError) {
          // For field errors, form components will display them inline
          if (error.status === 400 && error.isFieldErrors()) {
            return;
          }
          if (error.status === 401 || error.status === 403) {
            return;
          }
          toast.error(error.message || "An unexpected error occurred");
        }
      },
    },
  },
});
