output "parameter_arns" {
  description = "Map of secret name to SSM parameter ARN"
  value       = { for k, v in aws_ssm_parameter.secrets : k => v.arn }
}

output "parameter_name_prefix" {
  description = "SSM parameter path prefix for IAM policy scoping"
  value       = "/${var.project_name}/${var.environment}"
}
