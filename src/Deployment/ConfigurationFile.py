import os
import yaml

from Deployment.GitHub import GitHub
from typing import Optional, List


class ConfigurationFile:
    def __init__(self, configuration_filename: str):
        configuration = ConfigurationFile.__load_raw__(configuration_filename)
        self.environments = configuration["environments"]

    def get_aws_account_id(self, environment_id: str):
        """
        Return the AWS account ID for the specified environment
        :param environment_id: The environment you want the AWS account ID for
        :return: The AWS account ID
        """
        if environment_id not in self.environments.keys():
            raise Exception("Unknown environment ({environment_id}) requested".format(environment_id=environment_id))
        return self.environments[environment_id]["aws_account_id"]

    def get_aws_deployment_region(self, environment_id: str):
        """
        Return the AWS deployment region for the specified environment
        :param environment_id: The environment you want the AWS account ID for
        :return: The AWS account ID
        """
        if environment_id not in self.environments.keys():
            raise Exception("Unknown environment ({environment_id}) requested".format(environment_id=environment_id))
        return self.environments[environment_id]["aws_deployment_region"]

    def get_aws_deployment_cluster_name(self, environment_id: str):
        """
        Return the AWS deployment ECS cluster name for the specified environment
        :param environment_id: The environment you want the AWS account ID for
        :return: The AWS account ID
        """
        if environment_id not in self.environments.keys():
            raise Exception("Unknown environment ({environment_id}) requested".format(environment_id=environment_id))
        return self.environments[environment_id]["aws_deployment_cluster_name"]

    def get_container_names(self, environment_id: str) -> List[str]:
        """
        Return list of all container IDs for this environment
        :param environment_id: The environment you want the container list for
        :return: List of container IDs
        """
        if environment_id not in self.environments.keys():
            raise Exception("Unknown environment ({environment_id}) requested".format(environment_id=environment_id))

        return self.environments[environment_id]["containers"].keys()

    def is_container_run_required(self, environment_id: str, container_id: str):
        """
        Return flag indicating whether execution of the container is required during build process
        :param environment_id: The environment ID
        :param container_id: The container ID
        :return: The AWS account ID
        """
        if environment_id not in self.environments.keys():
            raise Exception("Unknown environment ({environment_id}) requested".format(environment_id=environment_id))
        if container_id not in self.environments[environment_id]["containers"].keys():
            raise Exception("Unknown container ({container_id}) requested".format(container_id=container_id))

        container = self.environments[environment_id]["containers"][container_id]
        run_key = 'run_during_deployment'
        if run_key not in container.keys():
            return False

        return container[run_key] == 1 or container[run_key] is True or container[run_key] == 'True' or container[run_key] == 'true' or container[run_key] == '1'

    def is_wait_service_stable_required(self, environment_id: str, container_id: str):
        """
        Return flag indicating whether the update process needs to wait for the service to stabilize before proceeding
        :param environment_id: The environment ID
        :param container_id: The container ID
        :return: The AWS account ID
        """
        if environment_id not in self.environments.keys():
            raise Exception("Unknown environment ({environment_id}) requested".format(environment_id=environment_id))
        if container_id not in self.environments[environment_id]["containers"].keys():
            raise Exception("Unknown container ({container_id}) requested".format(container_id=container_id))

        container = self.environments[environment_id]["containers"][container_id]
        run_key = 'wait_service_stable'
        if run_key not in container.keys():
            return False

        return container[run_key] == 1 or container[run_key] is True or container[run_key] == 'True' or container[run_key] == 'true' or container[run_key] == '1'


    def get_container_filename(self, environment_id: str, container_id: str):
        """
        Return the docker container filename for the specified environment/container
        :param environment_id: The environment ID
        :param container_id: The container ID
        :return: The AWS account ID
        """
        if environment_id not in self.environments.keys():
            raise Exception("Unknown environment ({environment_id}) requested".format(environment_id=environment_id))
        if container_id not in self.environments[environment_id]["containers"].keys():
            raise Exception("Unknown container ({container_id}) requested".format(container_id=container_id))

        return ConfigurationFile.__sanitize_filename__('{repository_root}/{container_filename}'.format(
            repository_root=GitHub.get_repository_root(),
            container_filename=self.environments[environment_id]["containers"][container_id]['dockerfile']
        ))

    def get_target(self, environment_id: str, container_id: str):
        """
        Return the docker target
        :param environment_id: The environment ID
        :param container_id: The container ID
        :return: The AWS account ID
        """
        if environment_id not in self.environments.keys():
            raise Exception("Unknown environment ({environment_id}) requested".format(environment_id=environment_id))
        if container_id not in self.environments[environment_id]["containers"].keys():
            raise Exception("Unknown container ({container_id}) requested".format(container_id=container_id))

        if 'target' not in self.environments[environment_id]["containers"][container_id].keys():
            return None

        return self.environments[environment_id]["containers"][container_id]['target']

    @staticmethod
    def __load_raw__(configuration_filename: str) -> dict:
        """
        Very basic validation of the configuration file
        :param configuration_filename: Path/filename to load
        :return: Dictionary containing the configuration
        :raises Exception: if file fails to validate
        """
        if os.path.exists(configuration_filename) is False:
            raise Exception('The deployment configuration file ({configuration_filename}) could not be located'.format(configuration_filename=configuration_filename))

        configuration: Optional[dict]
        configuration = None
        with open(configuration_filename, 'r') as stream:
            try:
                configuration = yaml.safe_load(stream)
            except yaml.YAMLError as exception:
                raise Exception('Failed to parse the configuration file ({exception}). Please check the files YAML syntax is valid and try again'.format(exception=exception))

        # Validate the file contents
        allowed_types = [
            'deployment_docker_compose'
        ]

        # Allowed versions of the configuration file for this tool
        allowed_versions = [1]

        # Check the required root level keys are present
        ConfigurationFile.__assert_dictionary_contains__(configuration, ['type', 'version', 'configuration'])

        # Validate the file is of the expected type
        if configuration['type'] not in allowed_types:
            raise Exception('The supplied file must be one of the allowed types ({allowed_types})'.format(allowed_types=', '.join(allowed_types)))

        # Validate the file is one of the allowed version numbers
        if configuration['version'] not in allowed_versions:
            raise Exception('The supplied deployment file version is not supported by this tool')

        # Validate the configuration tag
        ConfigurationFile.__assert_dictionary_contains__(configuration['configuration'], ['environments'])

        # Iterate the environments and ensure they are valid YML files
        for environment_id in configuration['configuration']['environments'].keys():
            environment = configuration['configuration']['environments'][environment_id]
            ConfigurationFile.__assert_dictionary_contains__(environment, ['aws_account_id', 'aws_deployment_region', 'containers'])
            for container_id in environment["containers"].keys():
                container = environment["containers"][container_id]
                ConfigurationFile.__assert_dictionary_contains__(container, ['dockerfile'])
                container_filename = ConfigurationFile.__sanitize_filename__("{path_repository_root}/{container_filename}".format(
                    path_repository_root=GitHub.get_repository_root(),
                    container_filename=container['dockerfile']
                ))
                if os.path.exists(container_filename) is False:
                    raise Exception('Could not locate specified container file ({container_filename}) in {environment} environment'.format(
                        container_filename=container_filename,
                        environment=environment
                    ))

                # Validate the expected entrypoint for the container exists
                entrypoint_filename = ConfigurationFile.__get_entrypoint_filename__(container_id=container_id)
                if os.path.exists(entrypoint_filename) is False:
                    print('WARNING: Failed to locate required Docker entrypoint script ({entrypoint_filename})'.format(
                        entrypoint_filename=entrypoint_filename
                    ))

        return configuration["configuration"]

    @staticmethod
    def __assert_dictionary_contains__(dictionary: dict, required_keys: list) -> None:
        """
        Validate the supplied dictionary contains the requested keys
        :param dictionary: The dictionary to test
        :param required_keys: The list of keys to assert exists
        :raises Exception: if one or more keys does not exist
        """
        error: bool
        error = False

        for key in required_keys:
            if key not in dictionary.keys():
                error = True
                print('The supplied dictionary did not contain the expected key ({key})'.format(key=key))

        if error is True:
            raise Exception('Error validating dictionary contents')

    @staticmethod
    def __get_entrypoint_filename__(container_id: str):
        """
        Return the docker entrypoint filename for the specified environment/container
        :param environment_id:
        :return: The AWS account ID
        """
        return ConfigurationFile.__sanitize_filename__("{path_repository_root}/docker/entrypoints/{container_id}.sh".format(
            path_repository_root=GitHub.get_repository_root(),
            container_id=container_id
        ))

    @staticmethod
    def __sanitize_filename__(filename: str) -> str:
        """
        Sanitize a user supplied filename to fix slashes and remove duplicate slashes
        :param filename: The original filename
        :return: The sanitized filename
        """
        filename = filename.replace('\\', '/')
        while '//' in filename:
            filename = filename.replace('//', '/')

        return filename
