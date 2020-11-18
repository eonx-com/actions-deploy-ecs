from typing import Dict, Optional, List, Any

from Aws.Client import Client as BaseClient
from Aws.Session import Session


class Client(BaseClient):
    def __init__(self, session: Session = None):
        """
        Configure ECS client
        """
        super().__init__(session=session, client='ssm')

    def get_parameters_by_path(self, path: str = '/', recursive: bool = False) -> List[str]:
        """
        Return list of SSM parmater names in the given path
        :param path: The path to search
        :param recursive: Boolean flag, if true will recurse all sub-paths
        """
        parameters = []
        get_parameters_by_path_result = self.get_client().get_parmeters_by_path(
            Path=path,
            Recursive=recursive
        )

        while True:
            for parameter in get_parameters_by_path_result['Parameters']:
                parameters.append(parameter['Name'])
            if 'NextToken' not in get_parameters_by_path_result.keys():
                break
            get_parmeters_by_path_result = self.get_client().get_parmeters_by_path(
                NextToken=get_parameters_by_path_result['NextToken'],
                Path=path,
                Recursive=recursive
            )

        return parameters

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
