environment = "prod"
aws_region  = "us-east-1"

domain_name          = "api.spotidex.xyz"
cors_allowed_origins = "https://spotidex.xyz"
allowed_hosts        = "*"

api_min_tasks = 1
api_max_tasks = 4

worker_min_tasks = 1
worker_max_tasks = 5
