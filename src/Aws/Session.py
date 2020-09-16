import boto3

from botocore.client import BaseClient
from typing import Optional


class Session:
    def __init__(
            self,
            aws_access_key_id: Optional[str] = None,
            aws_secret_access_key: Optional[str] = None,
            aws_session_token: Optional[str] = None,
            region_name: Optional[str] = None
    ):
        """
        Start new AWS session
        :param aws_access_key_id: AWS access key ID
        :param aws_secret_access_key: AWS secret access key
        :param aws_session_token: AWS temporary session token
        :param region_name: Default region when creating new connections
        """
        self.__session__ = boto3.session.Session(
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            aws_session_token=aws_session_token,
            region_name=region_name
        )
        self.__clients__ = {}

    def get_client(self, client: str) -> BaseClient:
        """
        Retrieve AWS client
        :param client: Client name
        :return: AWS client
        """
        if client not in self.__clients__.keys():
            self.__clients__[client] = self.__session__.client(client)

        return self.__clients__[client]
