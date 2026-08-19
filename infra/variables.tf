variable "aws_region" {
  description = "AWS region for the training infrastructure"
  type        = string
  default     = "us-east-1"
}

variable "github_repo" {
  description = "GitHub repository URL for shAI"
  type        = string
  default     = "https://github.com/Sergasgr/shai.git"
}

variable "s3_telemetry_bucket" {
  description = "S3 bucket containing the corporate telemetry database"
  type        = string
}

variable "s3_models_bucket" {
  description = "S3 bucket for storing trained model checkpoints and GGUF artifacts"
  type        = string
}

variable "iam_instance_profile" {
  description = "IAM Instance Profile name with S3 read/write permissions"
  type        = string
  default     = "shai-s3-upload-role"
}

variable "instance_type" {
  description = "EC2 GPU instance type for training"
  type        = string
  default     = "g4dn.xlarge"
}
