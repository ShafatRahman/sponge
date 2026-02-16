# AWS ECS Deployment

## Architecture

The backend runs on AWS ECS Fargate with two services:

| Service | Pool | Concurrency | CPU | Memory | Purpose |
|---------|------|-------------|-----|--------|---------|
| `api` | UvicornWorker | 3 workers | 512 | 1024 | Django REST API + SSE streaming |
| `worker` | prefork | 4 processes | 1024 | 2048 | Default and Detailed mode generation (Playwright fallback for CSR sites) |

All services auto-scale based on CPU utilization (target 70%).

## Docker Images

The backend Dockerfile produces two image targets:

- **`api`**: Lightweight image (~400MB). Django + gunicorn + uvicorn. No Playwright.
- **`worker`**: Full image (~1.2GB). Includes Playwright + Chromium for browser rendering.

Both share the same base layer for cache efficiency.

## ECS Task Definitions

Each service has its own task definition with:
- **`environment`**: Non-sensitive config (`DJANGO_SETTINGS_MODULE`, `CORS_ALLOWED_ORIGINS`)
- **`secrets`**: Sensitive values fetched from SSM Parameter Store at startup (see [SSM Secrets](./ssm-secrets.md))

The API service includes a health check:
```json
{
  "command": ["CMD-SHELL", "curl -f http://localhost:8000/api/health/ || exit 1"],
  "interval": 30,
  "timeout": 5,
  "retries": 3,
  "startPeriod": 60
}
```

## Networking

- VPC with public and private subnets across availability zones
- ALB in public subnets routes traffic to API tasks in private subnets
- Workers have no inbound access (outbound only for external APIs)
- All inter-service communication via AWS internal networking

## Updating Services

On merge to `main`, GitHub Actions:
1. Builds Docker image from `backend/Dockerfile`
2. Tags with commit SHA and `latest`
3. Pushes to ECR
4. Force-deploys both ECS services
5. Waits for API service stability
