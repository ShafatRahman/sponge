# CI/CD Pipelines

All CI/CD is managed by GitHub Actions in `.github/workflows/`.

## Workflows

### Backend CI (`ci-backend.yml`)

- **Trigger**: PR touching `backend/**`
- **Steps**: Checkout, setup Python + uv, `ruff check`, `ruff format --check`, `pytest`
- **Purpose**: Catch lint/format/test failures before merge

### Frontend CI (`ci-frontend.yml`)

- **Trigger**: PR touching `frontend/**`
- **Steps**: Checkout, setup Node, `npm ci`, `npm run check` (typecheck + lint + format), `npm run build`
- **Purpose**: Ensure frontend compiles and passes all quality checks

### Deploy Backend (`deploy-backend.yml`)

- **Trigger**: Push to `main` touching `backend/**`
- **Steps**:
  1. Configure AWS credentials (OIDC role assumption)
  2. Login to ECR
  3. Build Docker image (single build, tagged with SHA + latest)
  4. Push to ECR
  5. Force-deploy all three ECS services
  6. Wait for API stability
- **Secrets**: `AWS_ROLE_ARN`

### Terraform (`terraform.yml`)

- **Trigger**: Push/PR to `main` touching `infrastructure/**`
- **Plan job** (on PR):
  1. `terraform init`
  2. `terraform plan` with secrets passed as `-var`
  3. Post plan output as PR comment
- **Apply job** (on push to main):
  1. `terraform apply -auto-approve`
- **Secrets**: All infrastructure secrets (`SUPABASE_URL`, `REDIS_URL`, etc.) passed to Terraform for SSM parameter creation

### Docs Staleness Check (`docs-check.yml`)

- **Trigger**: PR touching `backend/**`, `frontend/**`, or `infrastructure/**`
- **Purpose**: Reminds to update docs when code changes (see [Docs Maintenance](../contributing/docs-maintenance.md))

## Security

- AWS credentials use OIDC role assumption (no long-lived access keys)
- Secrets are stored in GitHub repository secrets
- Terraform sensitive variables are marked `sensitive = true`
- ECS secrets come from SSM Parameter Store, never plain-text env vars
