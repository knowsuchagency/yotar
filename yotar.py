from contextlib import contextmanager
import subprocess as sp
import typing as T
import copy
import os


def shell(command: str, check=True, capture=False) -> sp.CompletedProcess:
    """
    Run the command in a shell.

    Args:
        command: the command to be run
        check: raise exception if return code not zero
        capture: if set to True, captures stdout and stderr,
                 making them available as stdout and stderr
                 attributes on the returned CompletedProcess.

                 This also means the command's stdout and stderr won't be
                 piped to FD 1 and 2 by default

    Returns: Completed Process

    """
    user = os.getlogin()
    print(f'{user}: {command}')
    process = sp.run(command,
                     check=check,
                     shell=True,
                     stdout=sp.PIPE if capture else None,
                     stderr=sp.PIPE if capture else None
                     )
    print()
    return process


@contextmanager
def cd(path_: Pathy):
    """Change the current working directory."""
    cwd = os.getcwd()
    os.chdir(path_)
    yield
    os.chdir(cwd)


@contextmanager
def env(**kwargs) -> T.Iterator[os._Environ]:
    """Set environment variables and yield new environment dict."""
    original_environment = copy.deepcopy(os.environ)

    for key, value in kwargs.items():
        os.environ[key] = value

    yield os.environ

    for key in os.environ:
        if key in kwargs and os.environ[key] == kwargs[key]:
            del os.environ[key]
        else:
            os.environ[key] = original_environment[key]


@contextmanager
def path(*paths: Pathy, prepend=False, expand_user=True) -> T.Iterator[T.List[str]]:
    """
    Add the paths to $PATH and yield the new $PATH as a list.

    Args:
        prepend: prepend paths to $PATH else append
        expand_user: expands home if ~ is used in path strings
    """
    paths_list: T.List[Pathy] = list(paths)

    paths_str_list: T.List[str]

    for index, _path in enumerate(paths_list):
        if not isinstance(_path, str):
            paths_str_list[index] = _path.__fspath__()
        elif expand_user:
            paths_str_list[index] = os.path.expanduser(_path)

    original_path = os.environ['PATH'].split(':')

    paths_str_list = paths_str_list + original_path if prepend else original_path + paths_str_list

    with env(PATH=':'.join(paths_str_list)):
        yield paths_str_list


@contextmanager
def quiet():
    """
    Suppress stdout and stderr.

    https://stackoverflow.com/questions/11130156/suppress-stdout-stderr-print-from-python-functions
    """

    # open null file descriptors
    null_file_descriptors = (
        os.open(os.devnull, os.O_RDWR),
        os.open(os.devnull, os.O_RDWR)
    )

    # save stdout and stderr
    stdout_and_stderr = (os.dup(1), os.dup(2))

    # assign the null pointers to stdout and stderr
    null_fd1, null_fd2 = null_file_descriptors
    os.dup2(null_fd1, 1)
    os.dup2(null_fd2, 2)

    yield

    # re-assign the real stdout/stderr back to (1) and (2)
    stdout, stderr = stdout_and_stderr
    os.dup2(stdout, 1)
    os.dup2(stderr, 2)

    # close all file descriptors.
    for fd in null_file_descriptors + stdout_and_stderr:
        os.close(fd)


if __name__ == '__main__':
    shell('mkdir -p foo')

    shell('pwd')

    with cd('foo'):
        shell('pwd')
        with env(foo='bar'):
            shell('echo $foo')
        # shouldn't output anything
        shell('echo $foo')

    p = shell('echo hello', capture=True)

    output = p.stdout.decode()

    print(f'The output was: {output}')

    shell('pwd')

    shell('ls')

    shell('rm -rf foo')

    shell('ls')

    with quiet():
        # shouldn't output anything
        print('hello, world')
