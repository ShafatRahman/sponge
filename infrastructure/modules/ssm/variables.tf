variable "project_name" {
  description = "Project name for SSM parameter path prefix"
  type        = string
}

variable "environment" {
  description = "Deployment environment (dev, prod)"
  type        = string
}

variable "secret_names" {
  description = "List of secret names to create as SSM parameters"
  type        = list(string)
}

variable "secret_values" {
  description = "Map of secret name to value for SSM SecureString parameters"
  type        = map(string)
  sensitive   = true
}
