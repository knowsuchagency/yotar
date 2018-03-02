
This story is about task automation and build tools.

Feel free to [**skip ahead**](#yotar) to the code and check out [the repo itself](https://github.com/knowsuchagency/yotar).

For a far more fleshed out example of the following, [**check out my cookiecutter**](https://github.com/knowsuchagency/python-package-template/blob/master/%7B%7Bcookiecutter.project_slug%7D%7D/run.py).

These are two separate, but inter-related domains, however, we're going to treat them both as the same requirement in this article for the sake of argumentation.

This means most of what is written is going to be more relevant for those who primarily
use Python (in particular, those writing packages) but hopefully there's something here for everyone.

## In the beginning, there were shell scripts.

But we found shell scripts to be difficultbecause even the best shell languages i.e. `zsh`, `bash`, `fish` 
have syntax and behavior that are much different than most other programming 
languages, which can make them hard to reason about. 

Everything (with few exceptions) is a string, it's almost impossible to avoid global
state, individual commands spawn subshells with their own environments and semantics,
and it's hard to write functions which do only one thing and chain those functions together easily.

From that primordial rigmarole, [GNU Make](https://www.gnu.org/software/make/) was born.

One of the benefits of Make is that it's language agnostic. 

As a sidenote, although this may not have been true at the time of Make's inception, 
I would argue that BASH is now so ubiquitous that it would be used as the lingua franca of task automation, 
if not for its wonkiness. Indeed, many developers use BASH in precisely that way. Masochists.

Among its other benefits, Make is more easily read than bash and allows one to document and chain "atomic" tasks
together.

However, many felt Make didn't go far enough, so other task runners/build automation tools were created.

Among them: Fabric, Ansible, Gulp, Grunt, Chef, Puppet, npm (in some capacity) - just to name a few.

Granted, what many of these tools offer is beyond the scope of Make or the typical bash script (automation on other machines through SSH, for example), but at the core of each of these tools is the intent to keep you from repeating yourself. It's task automation in one form or another, either for building software, automating dev-ops, or whatever.

**Enough pontification! Let's look at some code!**<a name="yotar"></a>

# [YOTAR](https://github.com/knowsuchagency/yotar)

## Your own Task Runner

Apart from the fact that Python is a great programming language to begin with, the standard library provides bevy of utilities that make it really powerful as a means of interacting with the operating system. 

In particular, we're going to focus primarily on 3 language features that are going go make our task automation a breeze. The [subprocess module](https://docs.python.org/3/library/subprocess.html), the [os module](https://docs.python.org/3/library/os.html), and [context managers](https://docs.python.org/3/library/contextlib.html#contextlib.contextmanager).

I should mention that I was inspired by the way fabric uses its [context managers](http://docs.fabfile.org/en/1.14/api/core/context_managers.html), but I found fabric to be overkill
for what I used it for, and I wanted one-less dependency and to have less magic in-general by using
the standard library to do the same things I was using Fabric for.

For our task runner, we're going to want 4 basic features (and one bonus) that will handle 95% of the tasks we commonly perform in a bash script or Makefile.

* a function that allows command execution in a bash shell spawned from our Python process
* a context manager that allows us to easily navigate the file-system
* a context manager that allows us to temporary alter environment variables
* a context manager that allows us to easily manipulate the $PATH variable temporarily
* **bonus**: a context manager that allows us to temporarily suppress stdout and stderr


```python
from contextlib import contextmanager
import subprocess as sp
import typing as T
import copy
import os
```

## The shell execution function

The following function will allow us to run commands in a bash
shell spawned from our interpreter. 

**Word to the wise**, make sure you trust the commands you're executing
using this function. 

Python won't be there to save you if you run something malicious
or just accidentally delete something important.

This is true of any task runner, or even bash script, but it's still worth
mentioning.


```python
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
```

## The cd context manager

This context manager just lets use change our current working
directory, returning to the directory we were in once it goes out of scope.


```python
@contextmanager
def cd(path_: T.Union[os.PathLike, str]):
    """Change the current working directory."""
    cwd = os.getcwd()
    os.chdir(path_)
    yield
    os.chdir(cwd)
```

## The environment variable context manager

This context manager just makes it so we can temporarily add or alter
existing environment variables, returning the environment to its
previous state once out of scope.


```python
@contextmanager
def env(**kwargs) -> dict:
    """Set environment variables and yield new environment dict."""
    original_environment = copy.deepcopy(os.environ)

    for key, value in kwargs.items():
        os.environ[key] = value

    yield os.environ

    for key in os.environ:
        if key not in original_environment:
            del os.environ[key]
        else:
            os.environ[key] = original_environment[key]
```

## The path context manager

This is just some sugar sprinkled over the `env` context manager, making it easier
to alter the $PATH environment variable.


```python
@contextmanager
def path(*paths: T.Union[os.PathLike, str], prepend=False) -> T.List[str]:
    """
    Add the paths to $PATH and yield the new $PATH as a list.

    Args:
        prepend: prepend paths to $PATH else append
    """
    paths = list(paths)

    for index, _path in enumerate(paths):
        if not isinstance(_path, str):
            paths[index] = _path.__fspath__()
        elif '~' in _path:
            paths[index] = os.path.expanduser(_path)

    original_path = os.environ['PATH'].split(':')

    paths = paths + original_path if prepend else original_path + paths

    with env(PATH=':'.join(paths)):
        yield paths
```

## Bonus: Quieting stdout and stderr

This context manager just makes it easy to suppress stdout and stderr temporarily.

It probably won't be used as much as the other tools we've written, but may yet come
in handy.


```python
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
```

## Usage

So the above already gets us pretty far. What does it look like in-practice?


```python
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

shell('rm -rf foo')

shell('ls')

with quiet():
    # shouldn't output anything
    print('hello, world')
```
stephanfitzpatrick: mkdir -p foo

stephanfitzpatrick: pwd
../yotar

stephanfitzpatrick: pwd
../yotar/foo

stephanfitzpatrick: echo $foo
bar

stephanfitzpatrick: echo $foo


stephanfitzpatrick: echo hello

The output was: hello

stephanfitzpatrick: pwd
../yotar

stephanfitzpatrick: rm -rf foo

stephanfitzpatrick: ls
yotar.py

## Command-line interface with composition and chaining?

So we already have some really handy utilites for doing 90% ish of the tasks on our local machine. What about getting function composition and chaining and a nice command-line interface? 

In part 2 we're going to use the excellent [Click](http://click.pocoo.org/) library by Armin Ronacher to do just that.

Part 3 will deal with combining our sripting utilities and the "tasks" we create with click with `setuptools` to bundle our tasks with our project's command-line interface.

If you want to go ahead and see how that works and start using that functionality now, feel free to check out my [cookiecutter](https://github.com/kalohq/python-package-template) that inspired this article.
