import os
import pathlib


class GitHub:
    @staticmethod
    def get_repository_root(path: str = "") -> str:
        """
        Find the closest GitHub repository root folder
        :path: The path in which we will start searching
        :return: The repositories root
        :raises Exception: if not found
        """
        path = pathlib.Path(path).absolute()

        found: bool
        found = False

        while found is False:
            if os.path.exists('{path}/.git'.format(path=path)) is True:
                return str(path)
            if path == '/':
                raise Exception('No GitHub repository found')
            path = path.parent
