# AWS SSM Parameter Store -- SecureString parameters for ECS secrets
#
# Each secret is stored at /<project>/<environment>/<KEY_NAME> and
# referenced by ARN in ECS task definitions via the `secrets` block.

resource "aws_ssm_parameter" "secrets" {
  for_each = toset(var.secret_names)

  name  = "/${var.project_name}/${var.environment}/${each.key}"
  type  = "SecureString"
  value = var.secret_values[each.key]

  tags = {
    Name        = each.key
    Environment = var.environment
    ManagedBy   = "terraform"
  }

  lifecycle {
    ignore_changes = [value]
  }
}
