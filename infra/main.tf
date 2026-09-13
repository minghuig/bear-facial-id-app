terraform {
  required_version = ">= 1.6, < 2.0"
  required_providers {
  aws = { source = "hashicorp/aws", version = "~> 5.100" }
  }
}
provider "aws" {
  region = var.region
}
variable "region" {
  default = "us-east-1"
}
variable "name" {
  default = "only-bears"
}
variable "instance_type" {
  default = "t3a.xlarge"
}
data "aws_caller_identity" "current" {
}
data "aws_availability_zones" "available" {
  state = "available"
}
data "aws_ssm_parameter" "ami" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}
resource "aws_vpc" "app" {
  cidr_block = "10.72.0.0/16"
  enable_dns_hostnames = true
  tags = { Name = var.name }
}
resource "aws_subnet" "app" {
  vpc_id = aws_vpc.app.id
  cidr_block = "10.72.1.0/24"
  availability_zone = data.aws_availability_zones.available.names[0]
  map_public_ip_on_launch = true
}
resource "aws_internet_gateway" "app" {
  vpc_id = aws_vpc.app.id
}
resource "aws_route_table" "app" {
  vpc_id = aws_vpc.app.id
  route {
  cidr_block = "0.0.0.0/0"
  gateway_id = aws_internet_gateway.app.id
}
}
resource "aws_route_table_association" "app" {
  subnet_id = aws_subnet.app.id
  route_table_id = aws_route_table.app.id
}
resource "aws_security_group" "app" {
  name = var.name
  vpc_id = aws_vpc.app.id
  # No inbound, including SSH. Authenticated SSM is the only access path.
  egress {
  from_port = 0
  to_port = 0
  protocol = "-1"
  cidr_blocks = ["0.0.0.0/0"]
}
}
resource "aws_s3_bucket" "app" {
  bucket = "${var.name}-${data.aws_caller_identity.current.account_id}-${var.region}"
  lifecycle {
  prevent_destroy = true
}
}
resource "aws_s3_bucket_public_access_block" "app" {
  bucket = aws_s3_bucket.app.id
  block_public_acls = true
  block_public_policy = true
  ignore_public_acls = true
  restrict_public_buckets = true
}
resource "aws_s3_bucket_server_side_encryption_configuration" "app" {
  bucket = aws_s3_bucket.app.id
  rule {
  apply_server_side_encryption_by_default {
    sse_algorithm = "AES256"
  }
}
}
resource "aws_s3_bucket_policy" "app" {
  bucket = aws_s3_bucket.app.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Deny", Principal = "*", Action = "s3:*", Resource = [aws_s3_bucket.app.arn, "${aws_s3_bucket.app.arn}/*"], Condition = { Bool = { "aws:SecureTransport" = "false" } } }] })
}
resource "aws_ecr_repository" "app" {
  for_each = toset(["api", "detector", "recognition"])
  name = "${var.name}/${each.key}"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
  scan_on_push = true
}
}
resource "aws_cloudwatch_log_group" "app" {
  name = "/${var.name}"
  retention_in_days = 7
}
resource "aws_iam_role" "app" {
  name = var.name
  assume_role_policy = jsonencode({ Version = "2012-10-17", Statement = [{ Effect = "Allow", Principal = { Service = "ec2.amazonaws.com" }, Action = "sts:AssumeRole" }] })
}
resource "aws_iam_role_policy_attachment" "ssm" {
  role = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}
resource "aws_iam_role_policy" "app" {
  role = aws_iam_role.app.id
  policy = jsonencode({ Version = "2012-10-17", Statement = [
    { Effect = "Allow", Action = ["s3:ListBucket"], Resource = [aws_s3_bucket.app.arn] },
    { Effect = "Allow", Action = ["s3:GetObject", "s3:PutObject"], Resource = ["${aws_s3_bucket.app.arn}/*"] },
    { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
    { Effect = "Allow", Action = ["ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart", "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:DescribeImages"], Resource = [for r in aws_ecr_repository.app : r.arn] },
    { Effect = "Allow", Action = ["logs:CreateLogStream", "logs:PutLogEvents"], Resource = "${aws_cloudwatch_log_group.app.arn}:*" }
  ] })
}
resource "aws_iam_instance_profile" "app" {
  name = var.name
  role = aws_iam_role.app.name
}
resource "aws_instance" "app" {
  ami = data.aws_ssm_parameter.ami.value
  instance_type = var.instance_type
  subnet_id = aws_subnet.app.id
  vpc_security_group_ids = [aws_security_group.app.id]
  iam_instance_profile = aws_iam_instance_profile.app.name
  credit_specification {
  cpu_credits = "standard"
}
  metadata_options {
  http_tokens = "required"
  http_put_response_hop_limit = 2
}
  root_block_device {
  volume_size = 40
  volume_type = "gp3"
  encrypted = true
}
  user_data = file("${path.module}/bootstrap.sh")
  tags = { Name = var.name }
  lifecycle {
  ignore_changes = [ami]
}
}
resource "aws_ebs_volume" "database" {
  availability_zone = aws_instance.app.availability_zone
  size = 10
  type = "gp3"
  encrypted = true
  tags = { Name = "${var.name}-database" }
  lifecycle {
  prevent_destroy = true
}
}
resource "aws_volume_attachment" "database" {
  device_name = "/dev/sdf"
  volume_id = aws_ebs_volume.database.id
  instance_id = aws_instance.app.id
}
output "instance_id" {
  value = aws_instance.app.id
}
output "region" {
  value = var.region
}
output "bucket" {
  value = aws_s3_bucket.app.id
}
output "database_volume_id" {
  value = aws_ebs_volume.database.id
}
output "registry" {
  value = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.region}.amazonaws.com"
}
output "name" {
  value = var.name
}
