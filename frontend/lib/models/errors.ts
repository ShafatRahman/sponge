import { type AxiosError } from "axios";

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code: string = "UNKNOWN") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }

  static fromAxiosError(error: AxiosError): ApiError {
    const status = error.response?.status ?? 0;
    const data = error.response?.data as Record<string, string> | undefined;

    // Server returns {"error": "..."} -- use that if available.
    const serverMessage = data?.error ?? data?.detail ?? data?.message;

    if (status === 429) {
      return new ApiError("Rate limit exceeded. Please try again later.", status, "RATE_LIMITED");
    }
    if (status === 401) {
      return new ApiError("Authentication required.", status, "UNAUTHORIZED");
    }
    if (status === 403) {
      return new ApiError(
        "You do not have permission to perform this action.",
        status,
        "FORBIDDEN",
      );
    }
    if (status === 404) {
      return new ApiError("Resource not found.", status, "NOT_FOUND");
    }
    if (status === 422) {
      return new ApiError(
        serverMessage ?? "The request was invalid. Please check your input.",
        status,
        "VALIDATION_ERROR",
      );
    }
    if (status >= 500) {
      return new ApiError(
        "Something went wrong on our end. Please try again later.",
        status,
        "SERVER_ERROR",
      );
    }

    // Network error (no response at all)
    if (status === 0) {
      return new ApiError(
        "Could not connect to the server. Please check your connection and try again.",
        0,
        "NETWORK_ERROR",
      );
    }

    // Fallback: use server message if it exists, otherwise generic
    return new ApiError(serverMessage ?? "An unexpected error occurred. Please try again.", status);
  }

  get isRateLimited(): boolean {
    return this.status === 429;
  }

  get isUnauthorized(): boolean {
    return this.status === 401;
  }

  get isServerError(): boolean {
    return this.status >= 500;
  }

  get isNetworkError(): boolean {
    return this.status === 0;
  }
}
