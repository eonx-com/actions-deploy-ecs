from subprocess import Popen, PIPE
from typing import Tuple


class Docker:
    @staticmethod
    def login(repository_url: str, username: str, password: bytes) -> Tuple[str, str]:
        """
        Login to the requested docker repository
        :param repository_url: Docker repository URL
        :param username: Repository username
        :param password: Repository password
        :raises: Exception on login error
        """
        process = Popen(['docker', 'login', '--username', username, '--password', password, repository_url], stdout=PIPE, stderr=PIPE)

        stdout_login, stderr_login = process.communicate()
        if process.returncode != 0:
            print(stderr_login.decode('utf-8').strip())
            raise Exception('Unexpected return code ({return_code}) received during Docker repository login'.format(
                return_code=process.returncode
            ))
        return stdout_login.decode('utf-8').strip(), stderr_login.decode('utf-8').strip()
