from weakref import WeakValueDictionary
import boto3
import json
import os
import botocore
from string import Template
import botocore.session

from regex import F

shield_arns = {}
waf_arns = {}
hosted_zone_arn_format = Template('arn:aws:route53:::$id')
eip_arn_format = Template('arn:aws:ec2:$region:account-id:eip-allocation/$id')

def lambda_handler(event, context):
    #in_scope_accounts = json.loads(os.environ['in_scope_account_list'])

    #for dest_account in in_scope_accounts["account_list"]:
        associate_waf_shield_for_account("395837851499")


def associate_waf_shield_for_account(dest_account):
    try:
        waf_account_connection = create_session(dest_account)
        get_resources_to_protect(waf_account_connection)
        associate_shield(waf_account_connection)
    except Exception as e:
        print("An exception occurred assuming account role:")
        raise e


def create_session(destination_account_id):

    print("Starting...")

    print("Assuming role in  destination account:")
    sts_connection = boto3.client('sts')

    waf_account_connection = sts_connection.assume_role(
        RoleArn=f"arn:aws:iam::{destination_account_id}:role/AtlantisRole",
        RoleSessionName="AtlantisRole",
    )

    if waf_account_connection['ResponseMetadata']['HTTPStatusCode'] != 200:
        response = "Error"
        return response

    ACCESS_KEY = waf_account_connection['Credentials']['AccessKeyId']
    SECRET_KEY = waf_account_connection['Credentials']['SecretAccessKey']
    SESSION_TOKEN = waf_account_connection['Credentials']['SessionToken']

    waf_account_session = boto3.Session(
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        aws_session_token=SESSION_TOKEN, region_name="us-east-1"
    )

    # waf_account_session = boto3.Session(profile_name="awsaml-933836905741", region_name="us-east-1")

    return waf_account_session


def get_resources_to_protect(waf_account_connection):

    cloudfront_client = waf_account_connection.client('cloudfront')

    distributions = cloudfront_client.list_distributions()
    if distributions['DistributionList']['Quantity'] > 0:
        for distribution in distributions['DistributionList']['Items']:
            shield_arns[distribution['Id']] = distribution['ARN']
    else:
        print("No CloudFront distributions detected.")

    route53_client = waf_account_connection.client('route53')
    hosted_zones = route53_client.list_hosted_zones()
    for zones in hosted_zones['HostedZones']:
        index = zones['Id'].rfind('/')
        if index != -1:
            zone_id = zones['Id'][index+1:]
        else:
            zone_id = zones['Id']

        zone_arn = hosted_zone_arn_format.safe_substitute(id=zones['Id'])
        shield_arns[zones['Name'] + zone_id] = zone_arn
        waf_arns[zones['Name'] + zone_id] = zone_arn

    # alb_client = waf_account_connection.client('elbv2')
    # loadbalancers = alb_client.describe_load_balancers()
    # for elb in loadbalancers['LoadBalancers']:
    #     shield_arns[elb['LoadBalancerName']] = elb['LoadBalancerArn']
    #     waf_arns[elb['LoadBalancerName']] = elb['LoadBalancerArn']

    # eip_client = waf_account_connection.client('ec2')
    # addresses = eip_client.describe_addresses()
    # if len(addresses['Addresses']) > 0:
    #     for eip_dict in addresses['Addresses']:
    #         eip_arn = eip_arn_format.safe_substitute(
    #             region=eip_dict['NetworkBorderGroup'], id=eip_dict['AllocationId'])
    #         shield_arns[eip_dict['AllocationId']] = eip_arn


def associate_shield(waf_account_connection):
    # Subscribe to shield and create default group

    shield_client = waf_account_connection.client('shield')

    # try:
    #   response =  shield_client.get_subscription_state()
    #   if response['SubscriptionState'] != 'ACTIVE':
    #       return
    #   print(response['SubscriptionState'])
    # except botocore.exceptions.ClientError as e:
    #     print("Unexpected error: %s" % e)
    #     raise e

    try:
      print("create_subscription")
      response =  shield_client.create_subscription()
    except shield_client.exceptions.ResourceAlreadyExistsException:
        print("Account already has shield enabled")
    except botocore.exceptions.ClientError as e:
        print("Unexpected error: %s" % e)
        raise e

    try:
        response = shield_client.create_protection_group(
            ProtectionGroupId='IS-SHIELD-PROTECTION-GRP-ALL',
            Aggregation='MAX',
            Pattern='ALL',
            Tags=[
                {
                    'Key': 'Owner',
                    'Value': 'Managed by Lambda'
                },
            ]
        )
    except shield_client.exceptions.ResourceAlreadyExistsException:
        print("Account already has protection group")
    except botocore.exceptions.ClientError as e:
        print("Unexpected error: %s" % e)
        raise e

    associate_resources_to_shield(shield_client)


def associate_resources_to_shield(shield_client):
    for name, arn in shield_arns.items():
        try:
            shield_client.create_protection(
                Name=name,
                ResourceArn=arn,
                Tags=[
                    {
                        'Key': 'Owner',
                        'Value': 'Created by IS Lambda'
                    }
                ]
            )
        except shield_client.exceptions.ResourceAlreadyExistsException:
            print("Resource already protected")
