variable "aws_region" {
  description = "AWS-compatible local region."
  type        = string
  default     = "ap-northeast-1"
}

variable "aws_endpoint" {
  description = "floci AWS-compatible endpoint URL."
  type        = string
  default     = "http://localhost:4566"
}
