import axios, { type AxiosInstance, type AxiosRequestConfig, type AxiosError } from "axios";
import { ApiError } from "@/lib/models/errors";
import { CaseTransformer } from "@/lib/utils/case-transform";
import { getSupabaseClient } from "@/lib/supabase/client";

/**
 * Singleton Axios wrapper that handles:
 * - Auth token injection from Supabase session
 * - snake_case <-> camelCase transformation
 * - 401 retry with token refresh
 * - Error normalization to ApiError
 */
export class ApiClient {
  private static instance: ApiClient;
  private axiosInstance: AxiosInstance;

  private constructor(baseURL: string) {
    this.axiosInstance = axios.create({
      baseURL,
      timeout: 30000,
      headers: { "Content-Type": "application/json" },
    });
    this.setupInterceptors();
  }

  static getInstance(): ApiClient {
    if (!ApiClient.instance) {
      const apiUrl = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(
        /\/+$/,
        "",
      );
      ApiClient.instance = new ApiClient(apiUrl);
    }
    return ApiClient.instance;
  }

  private setupInterceptors(): void {
    // Request: attach auth token and transform to snake_case
    this.axiosInstance.interceptors.request.use(async (config) => {
      const supabase = getSupabaseClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (session?.access_token) {
        config.headers.Authorization = `Bearer ${session.access_token}`;
      }

      if (config.data && typeof config.data === "object") {
        config.data = CaseTransformer.camelToSnake(config.data);
      }

      return config;
    });

    // Response: transform to camelCase and handle errors
    this.axiosInstance.interceptors.response.use(
      (response) => ({
        ...response,
        data: CaseTransformer.snakeToCamel(response.data),
      }),
      async (error: unknown) => {
        const axiosError = error as AxiosError;
        if (axiosError.response?.status === 401) {
          const supabase = getSupabaseClient();
          const { error: refreshError } = await supabase.auth.refreshSession();
          if (!refreshError && axiosError.config) {
            return this.axiosInstance.request(axiosError.config);
          }
        }
        throw ApiError.fromAxiosError(axiosError);
      },
    );
  }

  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.axiosInstance.get<T>(url, config);
    return response.data;
  }

  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.axiosInstance.post<T>(url, data, config);
    return response.data;
  }

  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.axiosInstance.delete<T>(url, config);
    return response.data;
  }
}
