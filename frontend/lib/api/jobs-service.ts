import { ApiClient } from "./api-client";
import {
  JobResponseSchema,
  JobStatusResponseSchema,
  type CreateJobRequest,
  type JobResponse,
  type JobStatusResponse,
} from "@/lib/models/job";

/**
 * Domain-specific API service for job operations.
 * Validates all API responses with Zod schemas at runtime.
 */
export class JobsService {
  private api: ApiClient;

  constructor(api?: ApiClient) {
    this.api = api ?? ApiClient.getInstance();
  }

  async create(request: CreateJobRequest): Promise<JobResponse> {
    const raw = await this.api.post<JobResponse>("/api/jobs/", request);
    return JobResponseSchema.parse(raw);
  }

  async getStatus(jobId: string): Promise<JobStatusResponse> {
    const raw = await this.api.get<JobStatusResponse>(`/api/jobs/${jobId}/`);
    return JobStatusResponseSchema.parse(raw);
  }

  async getHistory(): Promise<{ results: JobResponse[] }> {
    const raw = await this.api.get<{ results: JobResponse[] }>("/api/jobs/history/");
    return {
      results: raw.results.map((job) => JobResponseSchema.parse(job)),
    };
  }
}

// Singleton instance for convenience
let jobsServiceInstance: JobsService | null = null;

export function getJobsService(): JobsService {
  if (!jobsServiceInstance) {
    jobsServiceInstance = new JobsService();
  }
  return jobsServiceInstance;
}
