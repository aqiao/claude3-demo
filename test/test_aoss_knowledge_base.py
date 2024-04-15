from src.aoss_knowledge_base import AOSSKnowledgeBase
import boto3

aoss_client = boto3.client("opensearchserverless")
tool = {
    "name": "test",
    "model_id": "anthropic.claude-v2:1",
    "region": "us-east-1",
    "lambda_runtime": "python3.9",
    "lambda_handler": "test_lambda.lambda_handler",
    "lambda_env_variables": {}
}


def test_init():
    knowledge_base = AOSSKnowledgeBase(aoss_client, tool)
    print(knowledge_base.awsauth)
    print(knowledge_base.credentials)
