variable "project_name" { type = string }
variable "environment" { type = string }
variable "aws_region" { type = string }

variable "ssm_parameter_name_prefix" {
  description = "SSM parameter path prefix for IAM policy scoping (e.g. /sponge/prod)"
  type        = string
}
