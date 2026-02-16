variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "sponge"
}

variable "environment" {
  description = "Deployment environment (dev, prod)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "api_cpu" {
  description = "CPU units for the API service (1024 = 1 vCPU)"
  type        = number
  default     = 512
}

variable "api_memory" {
  description = "Memory (MiB) for the API service"
  type        = number
  default     = 1024
}

variable "worker_cpu" {
  description = "CPU units for Celery workers"
  type        = number
  default     = 1024
}

variable "worker_memory" {
  description = "Memory (MiB) for Celery workers"
  type        = number
  default     = 2048
}

variable "api_min_tasks" {
  type    = number
  default = 1
}

variable "api_max_tasks" {
  type    = number
  default = 4
}

variable "worker_min_tasks" {
  type    = number
  default = 1
}

variable "worker_max_tasks" {
  type    = number
  default = 5
}

variable "container_image" {
  description = "Docker image URI (ECR)"
  type        = string
  default     = ""
}

variable "domain_name" {
  description = "Domain name for HTTPS certificate (e.g. api.sponge.dev). Leave empty for HTTP-only."
  type        = string
  default     = ""
}

variable "cors_allowed_origins" {
  type    = string
  default = "https://sponge.vercel.app"
}

# --- Secrets (passed to SSM module for SecureString parameter creation) ---

variable "supabase_url" {
  type      = string
  sensitive = true
}

variable "supabase_secret_key" {
  type      = string
  sensitive = true
}

variable "redis_url" {
  type      = string
  sensitive = true
}

variable "openai_api_key" {
  type      = string
  sensitive = true
}

variable "django_secret_key" {
  type      = string
  sensitive = true
}

variable "langfuse_public_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "langfuse_secret_key" {
  type      = string
  sensitive = true
  default   = ""
}

variable "database_url" {
  description = "PostgreSQL connection string (Supabase)"
  type        = string
  sensitive   = true
}
