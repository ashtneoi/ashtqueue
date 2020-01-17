import sys
from os import getcwd, path


def project_path(x):
    return path.join(ROOT, x)


def activate():
    activator = project_path('.env/bin/activate_this.py')
    real_activator = project_path('activate_this.py')
    try:
        with open(real_activator) as f:
            code = compile(f.read(), activator, 'exec')
            exec(code, {'__file__': activator})
    except:
        raise Exception("Couldn't activate virtualenv")


ROOT = sys.path[0]
if not ROOT:
    ROOT = getcwd()


if __name__ == '__main__':
    activate()
