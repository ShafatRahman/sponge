variable "project_name" { type = string }
variable "environment" { type = string }
variable "aws_region" { type = string }

variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "alb_target_group_arn" { type = string }
variable "alb_security_group_id" { type = string }

variable "execution_role_arn" { type = string }
variable "task_role_arn" { type = string }

variable "container_image" { type = string }

variable "api_cpu" { type = number }
variable "api_memory" { type = number }
variable "api_min_tasks" { type = number }
variable "api_max_tasks" { type = number }

variable "worker_cpu" { type = number }
variable "worker_memory" { type = number }
variable "worker_min_tasks" { type = number }
variable "worker_max_tasks" { type = number }

variable "cors_allowed_origins" {
  description = "Non-sensitive CORS origins value"
  type        = string
}

variable "allowed_hosts" {
  description = "Django ALLOWED_HOSTS (comma-separated hostnames, no scheme)"
  type        = string
}

variable "ssm_parameter_arns" {
  description = "Map of secret name to SSM parameter ARN (from the ssm module)"
  type        = map(string)
}

variable "container_image_worker" {
  description = "Docker image for worker containers (includes Playwright)"
  type        = string
  default     = ""
}
