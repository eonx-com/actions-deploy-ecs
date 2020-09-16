from subprocess import PIPE, Popen


class AwsCli:
    @staticmethod
    def ecr_get_login_password(region: str) -> bytes:
        """
        Retrieve ECR repository login password for the specified region
        :param region: The AWS region you are logging into
        :return: Password
        :raises: Exception on error
        """
        command = ['aws', 'ecr', 'get-login-password', '--region', region]
        process = Popen(command, stdout=PIPE, stderr=PIPE)
        stdout_login, stderr_login = process.communicate()
        if process.returncode != 0:
            print(stderr_login.decode('utf-8').strip())
            raise Exception('Unexpected return code ({return_code}) received during Docker login'.format(
                return_code=process.returncode
            ))
        return stdout_login
