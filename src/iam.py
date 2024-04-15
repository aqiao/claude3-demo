import time

import boto3
import json
import src.global_options as op


class IAM:
    """
    Create IAM policies and roles for specific role
    Please note, tool is a global conception, it's direction like {name:'tool name',model_id:'titan-text-G1'}
    All relevant IAM resources start with tool_name
    lambda function name: {tool_name}_lambda
    agent policy name: {tool_name}_agent_policy
    lambda policy name: {tool_name}_lambda_policy
    agent role name: AmazonBedrockExecutionRoleForAgents_{tool_name}
    lambda role name: AmazonBedrockExecutionRoleForLambda_{tool_name}
    """

    def __init__(self, iam_client, tool):
        self.iam_client = iam_client
        self.tool = tool

    def create_agent_role(self):

        # check if the current role
        role_name = f"{op.AGENT_ROLE_PREFIX}{self.tool['name']}{op.AGENT_ROLE_SUFFIX}"
        role_arn = self.check_role_existed(role_name)
        if role_arn:
            # check if the policy includes InvokeModel permission
            if self.check_agent_role_policy(role_name) is None:
                self.create_agent_inline_policy(role_name)
                time.sleep(10)
        else:
            role_arn = self.create_agent_assume_role(role_name)
            # add in-line policy of InvokeModel
            self.create_agent_inline_policy(role_name)
            time.sleep(10)
        return role_arn

    def create_lambda_role(self):
        role_name = f"{op.LAMBDA_ROLE_PREFIX}{self.tool['name']}{op.LAMBDA_ROLE_SUFFIX}"
        role_arn = self.check_role_existed(role_name)
        if role_arn:
            # check if the policy includes InvokeModel permission
            if not self.check_lambda_role_policy(role_name):
                self.iam_client.attach_role_policy(RoleName=role_name, PolicyArn=op.LAMBDA_SERVICE_ROLE_POLICY_ARN)
                time.sleep(10)
        else:
            role_arn = self.create_lambda_assume_role(role_name)
            self.iam_client.attach_role_policy(RoleName=role_name, PolicyArn=op.LAMBDA_SERVICE_ROLE_POLICY_ARN)
            time.sleep(10)
        return role_arn

    def create_agent_assume_role(self, role_name):
        response = self.iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "bedrock.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )
        return response['Role']['Arn']

    def create_agent_inline_policy(self, role_name):
        policy_name = f"{self.tool['name']}{op.AGENT_POLICY_SUBFIX}"
        model_arn = f"arn:aws:bedrock:{self.tool['region']}::foundation-model/{self.tool['model_id']}"
        bucket_arn = f"arn:aws:s3:::{op.AGENT_BUCKET}"
        self.iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName=policy_name,
            PolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Action": "bedrock:InvokeModel",
                            "Resource": model_arn,
                        },
                        {
                            "Effect": "Allow",
                            "Action": "s3:ListBucket",
                            "Resource": bucket_arn,
                        },
                        {
                            "Effect": "Allow",
                            "Action": "s3:*",
                            "Resource": f"{bucket_arn}/*",
                        },
                    ],
                }
            )
        )

    def check_role_existed(self, role_name):
        try:
            response = self.iam_client.get_role(RoleName=role_name)
            return response['Role']['Arn']
        except self.iam_client.exceptions.NoSuchEntityException:
            return None

    def check_lambda_role_policy(self, role_name):
        """
        Check if current role can access, please note lambda policy is always manager policy
        :param role_name:
        :return:
        """
        try:
            response = self.iam_client.list_attached_role_policies(RoleName=role_name)
            attached_policies = response['AttachedPolicies']
            policies = list(filter(lambda x: x['PolicyName'] == op.LAMBDA_SERVICE_ROLE_POLICY_ARN, attached_policies))
            print(policies)
            return len(policies) > 0
        except self.iam_client.exceptions.NoSuchEntityException:
            return False

    def check_agent_role_policy(self, role_name):
        policy_name = f"{self.tool['name']}{op.AGENT_POLICY_SUBFIX}"
        try:
            response = self.iam_client.get_role_policy(RoleName=role_name, PolicyName=policy_name)
            return response['PolicyDocument']

        except self.iam_client.exceptions.NoSuchEntityException:
            return None

    def create_lambda_assume_role(self, role_name):
        response = self.iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
        )
        return response['Role']['Arn']
