resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# Security group for ECS tasks
resource "aws_security_group" "ecs_tasks" {
  name_prefix = "${var.project_name}-${var.environment}-ecs-"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-${var.environment}-ecs-sg" }

  lifecycle {
    create_before_destroy = true
  }
}

# CloudWatch log groups
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.project_name}-${var.environment}-api"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/ecs/${var.project_name}-${var.environment}-worker"
  retention_in_days = 30
}

locals {
  # Non-sensitive environment variables (safe to appear in task definition JSON)
  env_vars = [
    { name = "DJANGO_SETTINGS_MODULE", value = "config.settings.production" },
    { name = "CORS_ALLOWED_ORIGINS", value = var.cors_allowed_origins },
    { name = "ALLOWED_HOSTS", value = var.allowed_hosts },
    { name = "LANGFUSE_HOST", value = var.langfuse_host },
  ]

  # Sensitive values fetched from SSM Parameter Store at task startup
  secret_vars = [
    { name = "SUPABASE_URL", valueFrom = var.ssm_parameter_arns["SUPABASE_URL"] },
    { name = "SUPABASE_SECRET_KEY", valueFrom = var.ssm_parameter_arns["SUPABASE_SECRET_KEY"] },
    { name = "REDIS_URL", valueFrom = var.ssm_parameter_arns["REDIS_URL"] },
    { name = "DATABASE_URL", valueFrom = var.ssm_parameter_arns["DATABASE_URL"] },
    { name = "OPENAI_API_KEY", valueFrom = var.ssm_parameter_arns["OPENAI_API_KEY"] },
    { name = "DJANGO_SECRET_KEY", valueFrom = var.ssm_parameter_arns["DJANGO_SECRET_KEY"] },
    { name = "LANGFUSE_PUBLIC_KEY", valueFrom = var.ssm_parameter_arns["LANGFUSE_PUBLIC_KEY"] },
    { name = "LANGFUSE_SECRET_KEY", valueFrom = var.ssm_parameter_arns["LANGFUSE_SECRET_KEY"] },
    { name = "SENTRY_DSN", valueFrom = var.ssm_parameter_arns["SENTRY_DSN"] },
  ]

  worker_image = var.container_image_worker != "" ? var.container_image_worker : var.container_image
}

# --- API Service ---
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.project_name}-${var.environment}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.api_cpu
  memory                   = var.api_memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name  = "api"
    image = var.container_image
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    environment  = local.env_vars
    secrets      = local.secret_vars
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
    command = [
      "uv", "run", "gunicorn", "config.asgi:application",
      "--bind", "0.0.0.0:8000",
      "--worker-class", "uvicorn.workers.UvicornWorker",
      "--workers", "3", "--timeout", "120"
    ]
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/api/health/ || exit 1"]
      interval    = 10
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])
}

resource "aws_ecs_service" "api" {
  name            = "${var.project_name}-${var.environment}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = var.api_min_tasks
  launch_type     = "FARGATE"

  # Allow the app time to boot before ECS enforces ALB health checks.
  # Uvicorn workers take ~25s to start; 60s gives ample headroom.
  health_check_grace_period_seconds = 60

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [aws_security_group.ecs_tasks.id]
  }

  load_balancer {
    target_group_arn = var.alb_target_group_arn
    container_name   = "api"
    container_port   = 8000
  }
}

# --- Worker Service ---
resource "aws_ecs_task_definition" "worker" {
  family                   = "${var.project_name}-${var.environment}-worker"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.worker_cpu
  memory                   = var.worker_memory
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode([{
    name        = "worker"
    image       = local.worker_image
    environment = local.env_vars
    secrets     = local.secret_vars
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.worker.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "worker"
      }
    }
    command = [
      "uv", "run", "celery", "-A", "config", "worker",
      "--pool=prefork", "--concurrency=4", "-l", "info"
    ]
  }])
}

resource "aws_ecs_service" "worker" {
  name            = "${var.project_name}-${var.environment}-worker"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.worker.arn
  desired_count   = var.worker_min_tasks
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = var.private_subnet_ids
    security_groups = [aws_security_group.ecs_tasks.id]
  }
}

# --- Auto-scaling: API ---
resource "aws_appautoscaling_target" "api" {
  max_capacity       = var.api_max_tasks
  min_capacity       = var.api_min_tasks
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.api.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "api_cpu" {
  name               = "${var.project_name}-${var.environment}-api-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.api.resource_id
  scalable_dimension = aws_appautoscaling_target.api.scalable_dimension
  service_namespace  = aws_appautoscaling_target.api.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}

# --- Auto-scaling: Worker ---
resource "aws_appautoscaling_target" "worker" {
  max_capacity       = var.worker_max_tasks
  min_capacity       = var.worker_min_tasks
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.worker.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "worker_cpu" {
  name               = "${var.project_name}-${var.environment}-worker-cpu"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.worker.resource_id
  scalable_dimension = aws_appautoscaling_target.worker.scalable_dimension
  service_namespace  = aws_appautoscaling_target.worker.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
