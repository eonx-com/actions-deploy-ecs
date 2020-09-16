from typing import Dict, Optional, List, Any

from Aws.Client import Client as BaseClient
from Aws.Session import Session


class Client(BaseClient):
    def __init__(self, session: Session = None):
        """
        Configure ECS client
        """
        super().__init__(session=session, client='ssm')

    def put_parameter(self, path: str, value: str, secure: bool = False, allow_overwrite: bool = True):
        """
        Set an SSM parameter
        :param path: The SSM parameter path
        :param value: The value to store
        :param secure: Boolean flag, if true the value will be stored as a SecureString type
        :param allow_overwrite: Boolean flag, if true existing parameters will be overwritten without error
        """
        self.get_client().put_parameter(
            Name=path,
            Value=value,
            Type='SecureString' if secure is True else 'String',
            Overwrite=allow_overwrite
        )

    def get_parameter(self, path: str) -> str:
        """
        Get an SSM parameter
        :param path: The SSM parameter path
        :return: Parameter value
        """
        get_parameter_result = self.get_client().get_parameter(
            Name=path,
            WithDecryption=True
        )
        return get_parameter_result['Parameter']['Value']
