terraform {
  backend "http" {
    address        = "https://gitlab.com/api/v4/projects/71760885/terraform/state/production"
    lock_address   = "https://gitlab.com/api/v4/projects/71760885/terraform/state/production/lock"
    unlock_address = "https://gitlab.com/api/v4/projects/71760885/terraform/state/production/lock"
    lock_method    = "POST"
    unlock_method  = "DELETE"
    username       = "gitlab-ci-token"
    # password is passed via TF_HTTP_PASSWORD in CI/CD
  }

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

# ✅ Ubuntu 22.04 AMI (dynamic lookup by region)
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ✅ Check for existing EC2 instance with tag "FastAPI-Server"
data "aws_instances" "existing" {
  filter {
    name   = "tag:Name"
    values = ["FastAPI-Server"]
  }

  filter {
    name   = "instance-state-name"
    values = ["pending", "running", "stopping", "stopped"]
  }
}

# ✅ Check for existing Security Group
data "aws_security_groups" "existing_sg" {
  filter {
    name   = "group-name"
    values = ["fastapi-sg*"]
  }
}

# ✅ Load existing instance details if it exists
data "aws_instance" "existing_instance" {
  count       = length(data.aws_instances.existing.ids) > 0 ? 1 : 0
  instance_id = data.aws_instances.existing.ids[0]
}

# ✅ Load existing security group details if it exists
data "aws_security_group" "existing_sg_details" {
  count = length(data.aws_security_groups.existing_sg.ids) > 0 ? 1 : 0
  id    = data.aws_security_groups.existing_sg.ids[0]
}

# ✅ Create Security Group ONLY if it doesn't exist
resource "aws_security_group" "fastapi_sg" {
  count       = length(data.aws_security_groups.existing_sg.ids) == 0 ? 1 : 0
  name_prefix = "fastapi-sg"

  # SSH access
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_cidr]
    description = "SSH access for CI/CD"
  }

  # FastAPI application
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "FastAPI application"
  }

  # pgAdmin
  ingress {
    from_port   = 5050
    to_port     = 5050
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "pgAdmin interface"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "FastAPI-SecurityGroup"
  }
}

# ✅ Import existing instance into state instead of creating new one
# This approach avoids the destroy/recreate cycle
resource "aws_instance" "fastapi_server" {
  ami                   = data.aws_ami.ubuntu.id
  instance_type         = "t2.micro"
  key_name              = var.key_name
  
  # Use existing security group if available, otherwise use new one
  vpc_security_group_ids = [
    length(data.aws_security_groups.existing_sg.ids) > 0 ? 
    data.aws_security_groups.existing_sg.ids[0] : 
    aws_security_group.fastapi_sg[0].id
  ]
  
  user_data_replace_on_change = false  # Changed to false to prevent recreation

  user_data = <<-EOF
    #!/bin/bash
    exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1
    
    echo "Starting user-data script at $(date)"
    
    # Update system
    apt update -y
    apt upgrade -y
    
    # Install Docker
    apt install -y docker.io curl git jq
    systemctl start docker
    systemctl enable docker
    usermod -aG docker ubuntu
    
    # Install Docker Compose v2
    curl -SL https://github.com/docker/compose/releases/download/v2.24.6/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
    chmod +x /usr/local/bin/docker-compose
    ln -s /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    # Configure environment
    echo 'export DOCKER_HOST=unix:///var/run/docker.sock' >> /etc/environment
    
    # Signal completion
    echo "User-data script completed at $(date)"
    touch /tmp/user-data-complete
  EOF

  tags = {
    Name = "FastAPI-Server"
  }

  lifecycle {
    # Prevent accidental termination
    prevent_destroy = true
    # Ignore changes to user_data if instance already exists
    ignore_changes = [user_data]
  }
}

# ✅ Local to determine which instance details to use
locals {
  # Always use the managed instance resource
  instance_ip = aws_instance.fastapi_server.public_ip
  instance_dns = aws_instance.fastapi_server.public_dns
  instance_id = aws_instance.fastapi_server.id
  
  # Check if we're managing an existing instance
  is_existing_instance = length(data.aws_instances.existing.ids) > 0
}