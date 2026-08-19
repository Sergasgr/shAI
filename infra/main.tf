terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

data "aws_ami" "dlami" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["Deep Learning OSS Nvidia Driver AMI (Ubuntu 22.04)*"]
  }
}

resource "aws_instance" "shai_trainer" {
  ami           = data.aws_ami.dlami.id
  instance_type = var.instance_type
  
  instance_market_options {
    market_type = "spot"
  }

  iam_instance_profile = var.iam_instance_profile

  user_data = <<-EOF
              #!/bin/bash
              set -e
              
              echo "Starting shAI MLOps Pipeline on Cloud GPU..."
              
              curl -LsSf https://astral.sh/uv/install.sh | sh
              export PATH="/root/.local/bin:$PATH"
              
              git clone ${var.github_repo} /opt/shai
              cd /opt/shai
            
              echo "Downloading corporate telemetry data..."
              mkdir -p /root/.local/share/shai/models/checkpoints
              aws s3 cp s3://${var.s3_telemetry_bucket}/feedback.db /root/.local/share/shai/feedback.db
              
              aws s3 sync s3://${var.s3_models_bucket}/checkpoints/ /root/.local/share/shai/models/checkpoints/ || true
              
              while true; do
                  aws s3 sync /root/.local/share/shai/models/checkpoints/ s3://${var.s3_models_bucket}/checkpoints/
                  sleep 300
              done &
              SYNC_PID=$!
              
              uv sync
              uv run shai train
              
              kill $SYNC_PID
              aws s3 sync /root/.local/share/shai/models/checkpoints/ s3://${var.s3_models_bucket}/checkpoints/
              aws s3 cp shai-expert.gguf s3://${var.s3_models_bucket}/shai-expert-$(date +%s).gguf
              
              echo "Training complete. Upload successful."
              sudo shutdown -h now
              EOF

  tags = {
    Name = "shai-ephemeral-trainer"
  }
}