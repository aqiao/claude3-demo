import boto3
from src.iam import IAM
import src.global_options as op
import time
import logging
import json


class ActionGroup:
    """
    Read action schema and call create lambda function
    global variable tool structure:
    {"name": "test", "model_id":"amazon:titan.xxx","runtime":"python3.9", "zip_s3_path":"s3://test/a.zip"}
    """

    def __init__(self, lambda_client, iam_client, bedrock_build_client, tool):
        self.lambda_client = lambda_client
        self.tool = tool
        self.iam_client = iam_client
        self.iam = IAM(iam_client, tool)
        self.bedrock_build_client = bedrock_build_client

    def create_lambda_function(self):
        function_name = f"{self.tool['name']}{op.LAMBDA_SUFFIX}"
        runtime = self.tool['lambda_runtime']
        handler = self.tool['lambda_handler']
        env_variables = self.tool['lambda_env_variables']
        s3_key = f"{function_name}.zip"
        role_arn = self.iam.create_lambda_role()

        response = self.lambda_client.create_function(
            FunctionName=function_name,
            Runtime=runtime,
            Handler=handler,
            Role=role_arn,
            Code={'S3Bucket': op.AGENT_BUCKET, 'S3Key': s3_key},
            Environment={
                'Variables': env_variables,
            },
            Publish=True
        )
        waiter = self.lambda_client.get_waiter("function_active_v2")
        waiter.wait(FunctionName=function_name)
        return response["FunctionArn"]

    def grand_agent_invoke_lambda(self, agent_arn, lambda_arn):
        """
        Allow agent and lambda can access each other
        1. set from lambda role to allow bedrock invoke
        2. set from agent role to invoke lambda
        :param agent_arn:
        :param lambda_arn:
        :return:
        """
        agent_role_name = f"{op.AGENT_ROLE_PREFIX}{self.tool['name']}{op.AGENT_ROLE_SUFFIX}"
        agent_policy_name = f"{self.tool['name']}{op.AGENT_POLICY_SUBFIX}"
        agent_response = self.iam_client.get_role_policy(
            RoleName=agent_role_name,
            PolicyName=agent_policy_name
        )
        policy_doc = agent_response['PolicyDocument']
        # update agent in-line policy
        policy_doc['Statement'].append(
            {
                "Effect": "Allow",
                "Action": "lambda:InvokeFunction",
                "Resource": lambda_arn
            }
        )
        self.iam_client.put_role_policy(
            RoleName=agent_role_name,
            PolicyName=agent_policy_name,
            PolicyDocument=json.dumps(policy_doc)
        )

        self.lambda_client.add_permission(
            FunctionName=f"{self.tool['name']}{op.LAMBDA_SUFFIX}",
            SourceArn=agent_arn,
            StatementId="BedrockAccess",
            Action="lambda:InvokeFunction",
            Principal="bedrock.amazonaws.com",
        )
        time.sleep(10)

    def create_agent(self):
        name = f"{self.tool['name']}{op.AGENT_SUFFIX}"
        model_id = self.tool["model_id"]
        role_arn = self.iam.create_agent_role()
        instruction = """
            You are a friendly chat bot. You have access to a function called that returns
            information about the current date and time. When responding with date or time,
            please make sure to add the timezone UTC.
            """
        response = self.bedrock_build_client.create_agent(
            agentName=name,
            foundationModel=model_id,
            agentResourceRoleArn=role_arn,
            instruction=instruction,
        )
        self._wait_for_agent_status(response['agent']["agentId"], "NOT_PREPARED")
        # time.sleep(3)
        return response['agent']

    def create_agent_action_group(self, agent, action_group, lambda_arn):
        s3_key = f"{self.tool['name']}{op.LAMBDA_SUFFIX}.yaml"
        logging.log(1, 'yaml s3 key', s3_key)
        self.bedrock_build_client.create_agent_action_group(
            agentId=agent['agentId'],
            agentVersion=agent['agentVersion'],
            actionGroupName=action_group,
            actionGroupExecutor={'lambda': lambda_arn},
            apiSchema={
                's3': {
                    's3BucketName': op.AGENT_BUCKET,
                    's3ObjectKey': s3_key
                }
            }
        )

    def prepare_agent(self, agent_id):
        prepared_agent = self.bedrock_build_client.prepare_agent(agentId=agent_id)
        self._wait_for_agent_status(agent_id, "PREPARED")
        return prepared_agent

    def _wait_for_agent_status(self, agent_id, status):
        agent_status = self.bedrock_build_client.get_agent(agentId=agent_id)['agent']["agentStatus"]
        while agent_status != status:
            if agent_status == 'FAILED':
                break
            agent_status = self.bedrock_build_client.get_agent(agentId=agent_id)['agent']["agentStatus"]
            time.sleep(2)

    def init_agent(self):
        lambda_arn = self.create_lambda_function()
        agent = self.create_agent()
        prepared_agent = self.prepare_agent(agent['agentId'])
        group_name = f"{self.tool['name']}{op.AGENT_ACTION_GROUP_SUFFIX}"
        self.create_agent_action_group(prepared_agent, group_name, lambda_arn)
        self.grand_agent_invoke_lambda(agent['agentArn'], lambda_arn)
