from typing import List

import boto3
from botocore.client import BaseClient

from Aws.Session import Session


class Client:
    def __init__(self, client: str, session: Session = None):
        """
        Configure AWS client
        :param client: The client to create
        :param session: The AWS session
        """
        # If no session was supplied create a default session
        if session is None:
            session = Session()

        self.__client__ = session.get_client(client)

    def get_client(self) -> BaseClient:
        return self.__client__

    @staticmethod
    def __chunk_list__(source: List, size: int) -> List[List]:
        """
        Break a list into a list of lists
        :param source: The source list
        :param size: The size of each chunk
        :return: List of lists
        """
        result = []
        chunk = []
        for i in range(0, len(source)):
            if i % size == 0 and len(chunk) > 0:
                result.append(chunk)
                chunk = []
            chunk.append(source[i])

        if len(chunk) > 0:
            result.append(chunk)

        return result