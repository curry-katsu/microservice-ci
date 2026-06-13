provider "aws" {
  region                      = var.aws_region
  access_key                  = "test"
  secret_key                  = "test"
  s3_use_path_style           = true
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  endpoints {
    cloudwatch = var.aws_endpoint
    events     = var.aws_endpoint
    iam        = var.aws_endpoint
    lambda     = var.aws_endpoint
    logs       = var.aws_endpoint
    sqs        = var.aws_endpoint
    sts        = var.aws_endpoint
  }
}
