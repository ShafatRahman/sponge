# SSM Secrets Management

## Overview

All sensitive configuration for ECS containers is stored in AWS Systems Manager (SSM) Parameter Store as `SecureString` parameters. This ensures secrets never appear as plain-text environment variables in ECS task definitions.

## Architecture

```
GitHub Secrets
     |
     | (passed as -var to Terraform)
     v
Terraform SSM Module
     |
     | (creates SecureString parameters)
     v
AWS SSM Parameter Store
     |
     | (ECS fetches at container startup via `secrets` block)
     v
ECS Container Environment Variables
```

## SSM Parameter Naming

Parameters follow the convention: `/{project}/{environment}/{KEY_NAME}`

Example for production:
```
/sponge/prod/SUPABASE_URL
/sponge/prod/SUPABASE_SECRET_KEY
/sponge/prod/REDIS_URL
/sponge/prod/DATABASE_URL
/sponge/prod/OPENAI_API_KEY
/sponge/prod/DJANGO_SECRET_KEY
/sponge/prod/LANGFUSE_PUBLIC_KEY
/sponge/prod/LANGFUSE_SECRET_KEY
```

## Terraform Configuration

The SSM module (`infrastructure/modules/ssm/`) creates one `aws_ssm_parameter` resource per secret:

```hcl
resource "aws_ssm_parameter" "secrets" {
  for_each = var.secrets
  name     = "/${var.project_name}/${var.environment}/${each.key}"
  type     = "SecureString"
  value    = each.value
}
```

The ECS module references these parameters via ARN in the container `secrets` block:

```hcl
secrets = [
  { name = "DATABASE_URL", valueFrom = var.ssm_parameter_arns["DATABASE_URL"] },
  ...
]
```

## IAM Permissions

The ECS execution role has `ssm:GetParameters` and `ssm:GetParameter` scoped to the project's parameter path:

```
arn:aws:ssm:{region}:*:parameter/sponge/*
```

## Updating Secrets

To update a secret value:

1. Update the value in GitHub repository secrets
2. Re-run the Terraform workflow (it will update the SSM parameter)
3. Force-deploy the ECS services to pick up the new value

Note: The SSM module uses `lifecycle { ignore_changes = [value] }` to prevent Terraform from reverting manual changes. Remove this if you want Terraform to be the sole source of truth.
