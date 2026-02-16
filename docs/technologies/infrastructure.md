# Infrastructure Technologies

## Cloud & Compute

### AWS ECS Fargate

- **What**: Serverless container orchestration (no EC2 instances to manage).
- **Why**: Scales API and workers independently. Pay per task. No server maintenance.
- **Our usage**: Two ECS services: `api`, `worker`. Auto-scaling on CPU utilization.
- **Docs**: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/

### AWS SSM Parameter Store

- **What**: Secure, hierarchical storage for configuration and secrets.
- **Why**: Secrets are never stored as plain-text environment variables in ECS task definitions.
- **Our usage**: 9 SecureString parameters at `/{project}/{environment}/{KEY}`. ECS pulls them via the `secrets` block at container startup.
- **Docs**: https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-parameter-store.html

### AWS ALB (Application Load Balancer)

- **What**: Layer 7 load balancer.
- **Why**: Routes HTTP traffic to ECS API tasks. Health checks via `/api/health/`.
- **Docs**: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/

### AWS ECR (Elastic Container Registry)

- **What**: Docker container registry.
- **Why**: Private registry for backend Docker images, integrated with ECS.
- **Docs**: https://docs.aws.amazon.com/AmazonECR/latest/userguide/

## IaC & CI/CD

### Terraform

- **What**: Infrastructure as Code tool.
- **Why**: Declarative, reproducible infrastructure. Modular structure for reusability.
- **Our usage**: `infrastructure/` with modules for VPC, ECR, ECS, ALB, IAM, SSM. State in S3.
- **Docs**: https://developer.hashicorp.com/terraform/docs

### GitHub Actions

- **What**: CI/CD platform.
- **Why**: Native GitHub integration. Runs on push/PR. Free for public repos.
- **Our usage**: Backend CI (ruff), Frontend CI (typecheck + lint + build), Backend Deploy (Docker + ECR + ECS), Terraform (plan on PR, apply on merge).
- **Docs**: https://docs.github.com/en/actions

### Docker

- **What**: Container runtime.
- **Why**: Consistent environments from dev to prod. Multi-stage builds for optimized images.
- **Our usage**: Multi-stage `Dockerfile` with `api` (lightweight) and `worker` (includes Playwright) targets. `docker-compose.yml` for local dev.
- **Docs**: https://docs.docker.com/

## Hosting

### Vercel

- **What**: Frontend hosting platform optimized for Next.js.
- **Why**: Zero-config Next.js deployment. Auto-deploy on push. Edge network.
- **Our usage**: Frontend deployed from `frontend/` directory. Environment variables in dashboard.
- **Docs**: https://vercel.com/docs

### Upstash Redis

- **What**: Serverless Redis service.
- **Why**: Pay-per-request pricing. TLS by default. No server management.
- **Our usage**: Celery broker, cache, rate limiting, SSE pub/sub.
- **Docs**: https://upstash.com/docs/redis
