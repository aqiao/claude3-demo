import os

import boto3
from src.iam import IAM
import pytest

tool = {
    "name": "test",
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    "region": "us-east-1"
}

boto3.setup_default_session(profile_name='bedrocker')
iam_client = boto3.client("iam")
iam = IAM(iam_client, tool)


def test_check_role_existed():
    assert iam.check_role_existed("AmazonBedrockExecutionRoleForAgents_bedrock-demo-role") == True


def test_create_agent_invoke_permission():
    role_name = 'AmazonBedrockExecutionRoleForAgents_bedrock-demo-role'
    policy_name = f"{tool['name']}_agent_policy"
    iam.create_agent_inline_policy(role_name, policy_name)


def test_create_agent_role():
    iam.create_agent_role()
    role_name = f"AmazonBedrockExecutionRoleForAgents_{tool['name']}_agent_role"
    assert iam.check_role_existed(role_name) == True


def test_check_lambda_role_policy():
    role_name = f"AmazonBedrockExecutionRoleForAgents_{tool['name']}_agent_role"
    assert iam.check_lambda_role_policy(role_name) == False


def test_create_lambda_role():
    role_name = f"AmazonBedrockExecutionRoleForLambda_{tool['name']}_lambda_role"
    iam.create_lambda_role()
    assert iam.check_role_existed(role_name) is not None


def test_create_agent_assume_role():
    role_name = f"AmazonBedrockExecutionRoleForLambda_{tool['name']}_lambda_role"
    iam.create_lambda_assume_role(role_name)

