terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "sponge-terraform-state"
    key    = "terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

module "vpc" {
  source       = "./modules/vpc"
  project_name = var.project_name
  environment  = var.environment
  vpc_cidr     = var.vpc_cidr
  aws_region   = var.aws_region
}

module "ecr" {
  source       = "./modules/ecr"
  project_name = var.project_name
}

# SSM Parameter Store -- stores all secrets as SecureString parameters
module "ssm" {
  source       = "./modules/ssm"
  project_name = var.project_name
  environment  = var.environment

  secret_names = [
    "SUPABASE_URL",
    "SUPABASE_SECRET_KEY",
    "REDIS_URL",
    "DATABASE_URL",
    "OPENAI_API_KEY",
    "DJANGO_SECRET_KEY",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "SENTRY_DSN",
  ]

  secret_values = {
    SUPABASE_URL        = var.supabase_url
    SUPABASE_SECRET_KEY = var.supabase_secret_key
    REDIS_URL           = var.redis_url
    DATABASE_URL        = var.database_url
    OPENAI_API_KEY      = var.openai_api_key
    DJANGO_SECRET_KEY   = var.django_secret_key
    LANGFUSE_PUBLIC_KEY = var.langfuse_public_key
    LANGFUSE_SECRET_KEY = var.langfuse_secret_key
    SENTRY_DSN          = var.sentry_dsn
  }
}

module "iam" {
  source       = "./modules/iam"
  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region

  ssm_parameter_name_prefix = module.ssm.parameter_name_prefix
}

module "alb" {
  source            = "./modules/alb"
  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  domain_name       = var.domain_name
}

module "ecs" {
  source       = "./modules/ecs"
  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region

  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  alb_target_group_arn  = module.alb.target_group_arn
  alb_security_group_id = module.alb.security_group_id

  execution_role_arn = module.iam.execution_role_arn
  task_role_arn      = module.iam.task_role_arn

  container_image = var.container_image != "" ? var.container_image : "${module.ecr.repository_url}:latest"

  api_cpu       = var.api_cpu
  api_memory    = var.api_memory
  api_min_tasks = var.api_min_tasks
  api_max_tasks = var.api_max_tasks

  worker_cpu       = var.worker_cpu
  worker_memory    = var.worker_memory
  worker_min_tasks = var.worker_min_tasks
  worker_max_tasks = var.worker_max_tasks

  # Non-sensitive config
  cors_allowed_origins = var.cors_allowed_origins
  allowed_hosts        = var.allowed_hosts

  # SSM ARNs for ECS secrets block (fetched from SSM at task startup)
  ssm_parameter_arns = module.ssm.parameter_arns
}
