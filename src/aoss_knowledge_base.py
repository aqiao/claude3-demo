import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import botocore
import time


class AOSSKnowledgeBase:
    def __init__(self,aoss_client, tool, agent_id):
        self.aoss_client = aoss_client
        self.credentials = boto3.Session().get_credentials()
        self.tool = tool
        self.awsauth=AWS4Auth(self.credentials.access_key,
                              self.credentials.secret_key,
                              tool['region'],
                              'aoss',
                              session_token=self.credentials.token)

    def create_knowledge_base(self):
        pass


