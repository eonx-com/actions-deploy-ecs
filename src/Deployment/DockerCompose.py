import hashlib
import yaml

from subprocess import Popen, PIPE
from typing import Tuple


# noinspection DuplicatedCode
class DockerCompose:
    @staticmethod
    def create_build_file(context: str, container_id: str, environment_id: str, dockerfile: str, image: str, version: str = '3.7') -> str:
        """
        Create a docker-compose YML file
        :param context: The image context
        :param container_id: The ID of the docker container (e.g. 'api')
        :param environment_id: The AWS environment ID
        :param dockerfile: The dockerfile location
        :param image: The ECR image URL
        :param version: The docker-compose version (defaults to 3.7)
        :return: The newly created filename
        """
        # Construct the YML object
        docker_compose = {
            'version': version,
            'services': {
                container_id: {
                    'build': {
                        'context': context,
                        'dockerfile': dockerfile,
                        'args': {
                            'DOCKER_CONTAINER_PATH': 'aws',
                        }
                    },
                    'image': image,
                    'environment': {
                        'AWS_ECS_TASK_NAME': container_id,
                        'AWS_ENVIRONMENT': environment_id
                    }
                }
            }
        }
        docker_compose_yml = str.encode(yaml.dump(docker_compose, sort_keys=False))

        # Create temporary docker-compose YML file
        filename = '/tmp/docker-compose-{container_id}-{hash}.yml'.format(
            container_id=container_id,
            hash=hashlib.sha512(docker_compose_yml).hexdigest()
        )
        file = open(filename, 'w')
        file.write(docker_compose_yml.decode('utf-8'))
        file.close()

        # Return the filename and file contents
        return filename

    @staticmethod
    def build(filename: str) -> Tuple[str, str]:
        """
        Build docker-compose container
        :param filename: The full path/filename of the docker-compose.yml file
        :returns: Tuple containing the stdout and stderr stream contents
        :raises: Exception on error
        """
        process = Popen(['docker-compose', '-f', filename, 'build', '--no-cache'], stdout=PIPE, stderr=PIPE)
        stdout_build, stderr_build = process.communicate()
        if process.returncode != 0:
            print(stderr_build.decode('utf-8').strip())
            raise Exception('Unexpected return code ({return_code}) received during container build process'.format(
                return_code=process.returncode
            ))
        return stdout_build.decode('utf-8').strip(), stderr_build.decode('utf-8').strip()

    @staticmethod
    def push(filename: str) -> Tuple[str, str]:
        """
        Push docker-compose container
        :param filename: The full path/filename of the docker-compose.yml file
        :returns: Tuple containing the stdout and stderr stream contents
        :raises: Exception on error
        """
        process = Popen(['docker-compose', '-f', filename, 'push'], stdout=PIPE, stderr=PIPE)
        stdout_push, stderr_push = process.communicate()
        if process.returncode != 0:
            print(stderr_push.decode('utf-8').strip())
            raise Exception('Unexpected return code ({return_code}) received during container build process'.format(
                return_code=process.returncode
            ))
        return stdout_push.decode('utf-8').strip(), stderr_push.decode('utf-8').strip()
