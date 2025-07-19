# ✅ Output instance details using the managed resource
output "instance_public_ip" {
  description = "Public IP of the FastAPI server"
  value       = aws_instance.fastapi_server.public_ip
}

output "instance_public_dns" {
  description = "Public DNS of the FastAPI server"
  value       = aws_instance.fastapi_server.public_dns
}

output "instance_id" {
  description = "Instance ID of the FastAPI server"
  value       = aws_instance.fastapi_server.id
}

output "infrastructure_status" {
  description = "Whether infrastructure was reused or newly created"
  value = local.is_existing_instance ? (
    "REUSED - Managing existing infrastructure"
  ) : (
    "CREATED - New infrastructure deployed"
  )
}

output "security_group_id" {
  description = "Security Group ID (existing or newly created)"
  value = length(data.aws_security_groups.existing_sg.ids) > 0 ? (
    data.aws_security_groups.existing_sg.ids[0]
  ) : (
    length(aws_security_group.fastapi_sg) > 0 ? aws_security_group.fastapi_sg[0].id : ""
  )
}