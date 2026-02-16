import { z } from "zod";

export const JobModeSchema = z.enum(["default", "detailed"]);
export type JobMode = z.infer<typeof JobModeSchema>;

export const JobStatusSchema = z.enum([
  "pending",
  "discovering",
  "extracting",
  "enhancing",
  "generating",
  "completed",
  "failed",
  "cancelled",
]);
export type JobStatus = z.infer<typeof JobStatusSchema>;

export const CreateJobRequestSchema = z.object({
  url: z.string().url(),
  mode: JobModeSchema,
  maxUrls: z.number().int().min(1).max(100).optional(),
});
export type CreateJobRequest = z.infer<typeof CreateJobRequestSchema>;

export const JobResponseSchema = z.object({
  id: z.string().uuid(),
  url: z.string().url(),
  mode: JobModeSchema,
  status: JobStatusSchema,
  createdAt: z.string(),
  updatedAt: z.string(),
  completedAt: z.string().nullable(),
});
export type JobResponse = z.infer<typeof JobResponseSchema>;

export const ProgressSchema = z.object({
  phase: z.string(),
  message: z.string(),
  urlsFound: z.number().optional(),
  completed: z.number().optional(),
  total: z.number().optional(),
  currentUrl: z.string().optional(),
});
export type Progress = z.infer<typeof ProgressSchema>;

export const JobResultSchema = z.object({
  llmsTxt: z.string(),
  llmsFullTxtUrl: z.string().nullable().optional(),
  totalPages: z.number(),
  pagesProcessed: z.number(),
  pagesFailed: z.number().default(0),
  generationTimeSeconds: z.number(),
  llmCallsMade: z.number().default(0),
  llmCostUsd: z.number().default(0),
});
export type JobResult = z.infer<typeof JobResultSchema>;

export const JobStatusResponseSchema = z.object({
  id: z.string(),
  status: JobStatusSchema,
  progress: ProgressSchema.nullable(),
  result: JobResultSchema.nullable(),
  error: z.string().nullable(),
});
export type JobStatusResponse = z.infer<typeof JobStatusResponseSchema>;
