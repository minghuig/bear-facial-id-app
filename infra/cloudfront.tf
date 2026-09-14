variable "enable_public_mvp" {
  type    = bool
  default = false
}
variable "public_site_enabled" {
  type    = bool
  default = false
}

resource "aws_cloudfront_vpc_origin" "app" {
  count = var.enable_public_mvp ? 1 : 0
  vpc_origin_endpoint_config {
    name                   = "${var.name}-private"
    arn                    = aws_instance.app.arn
    http_port              = 8080
    https_port             = 443
    origin_protocol_policy = "http-only"
    origin_ssl_protocols {
      items    = ["TLSv1.2"]
      quantity = 1
    }
  }
}

data "aws_security_group" "cloudfront_origin" {
  count = var.enable_public_mvp ? 1 : 0
  filter {
    name   = "group-name"
    values = ["CloudFront-VPCOrigins-Service-SG"]
  }
  vpc_id     = aws_vpc.app.id
  depends_on = [aws_cloudfront_vpc_origin.app, aws_cloudfront_distribution.app]
}

resource "aws_security_group_rule" "cloudfront_origin" {
  count                    = var.enable_public_mvp ? 1 : 0
  type                     = "ingress"
  security_group_id        = aws_security_group.app.id
  source_security_group_id = data.aws_security_group.cloudfront_origin[0].id
  from_port                = 8080
  to_port                  = 8080
  protocol                 = "tcp"
  description              = "Private CloudFront VPC origin only"
}

data "aws_cloudfront_cache_policy" "disabled" {
  count = var.enable_public_mvp ? 1 : 0
  name  = "Managed-CachingDisabled"
}
data "aws_cloudfront_origin_request_policy" "viewer" {
  count = var.enable_public_mvp ? 1 : 0
  name  = "Managed-AllViewer"
}

resource "aws_cloudfront_distribution" "app" {
  count               = var.enable_public_mvp ? 1 : 0
  enabled             = var.public_site_enabled
  comment             = "Only Bears invite-only MVP"
  default_root_object = "index.html"
  price_class         = "PriceClass_100"
  origin {
    domain_name = aws_instance.app.private_dns
    origin_id   = "only-bears-private"
    vpc_origin_config {
      vpc_origin_id = aws_cloudfront_vpc_origin.app[0].id
    }
  }
  default_cache_behavior {
    target_origin_id         = "only-bears-private"
    viewer_protocol_policy   = "redirect-to-https"
    allowed_methods          = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods           = ["GET", "HEAD"]
    cache_policy_id          = data.aws_cloudfront_cache_policy.disabled[0].id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.viewer[0].id
    compress                 = true
  }
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }
  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

output "public_url" {
  value = var.enable_public_mvp ? "https://${aws_cloudfront_distribution.app[0].domain_name}" : null
}
