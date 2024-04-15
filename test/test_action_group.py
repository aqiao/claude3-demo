import boto3
from src.iam import IAM
from src.action_group import ActionGroup

agent_config = {
    "name": "test",
    "model_id": "anthropic.claude-v2:1",
    "region": "us-east-1",
    "lambda_runtime": "python3.9",
    "lambda_handler": "test_lambda.lambda_handler",
    "lambda_env_variables": {},
    "bucket": "bedrock-agent-tool-repo"
}

boto3.setup_default_session(profile_name='bedrocker')
iam_client = boto3.client("iam")
lambda_client = boto3.client('lambda')
agent_client = boto3.client('bedrock-agent')

iam = IAM(iam_client, agent_config)
action_group = ActionGroup(lambda_client, iam_client, agent_client, agent_config)


def test_create_lambda_function():
    action_group.create_lambda_function()


def test_init_agent():
    action_group.init_agent()


def test_create_agent():
    action_group.create_agent()


def test_prepare_agent():
    action_group.prepare_agent(agent_id="T6ZL80TQG0")


def test_grand_agent_invoke_lambda():
    agent_arn = "arn:aws:bedrock:us-east-1:975050069421:agent/TDRD5SWE0F"
    lambda_arn = "arn:aws:lambda:us-east-1:975050069421:function:test_lambda"
    action_group.grand_agent_invoke_lambda(agent_arn, lambda_arn)


def test_init_agent():
    action_group.init_agent()
