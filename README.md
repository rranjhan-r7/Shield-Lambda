# Overview

Set of lambda functions to support Shield and WAF rollout

I used [python-lambda-local](https://pypi.org/project/python-lambda-local)  python module to run these lambdas:

In shield-lambda/shield/shield_associate folder:

1. use Awssaml to generate the credentials
2. python-lambda-local -f lambda_handler  shield_associate.py event.json -t 400  