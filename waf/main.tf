
# Associate WAF 
data "archive_file" "waf_shield_associate" {
  output_path      = ".terraform/files/waf_shield_associate.zip"
  type             = "zip"
  source_dir       = "${path.module}/waf_shield_associate"
  output_file_mode = "0666"
}

resource "aws_lambda_function" "waf_shield_associate" {
  filename         = data.archive_file.waf_shield_associate.output_path
  function_name    = "IS-Associate-WAF-SHIElD"
  handler          = "waf_shield_associate.lambda_handler"
  source_code_hash = data.archive_file.waf_shield_associate.output_base64sha256
  runtime          = "python3.8"
  memory_size      = "128"
  timeout          = 300
  tags             = {}
  environment {
    variables = {
      in_scope_account_list = "{\"account_list\":[\"464399329349\"]}"
    }
  }
}