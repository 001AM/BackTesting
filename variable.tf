variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "key_name" {
  description = "EC2 Key Pair name"
  type        = string
}

variable "allowed_cidr" {
  description = "CIDR block allowed to access the instance"
  type        = string
  default     = "0.0.0.0/0"  # Restrict this to your IP for security
}