from __future__ import absolute_import, division, print_function

import os
import os.path
import sys
import subprocess

import pytest


PYTEST_PATH = (os.path.abspath(pytest.__file__.rstrip("oc"))
               .replace("$py.class", ".py"))


@pytest.fixture
def popen(request):
    env = os.environ.copy()
    cwd = os.getcwd()
    pythonpath = [cwd]
    if env.get('PYTHONPATH'):
        pythonpath.append(env['PYTHONPATH'])
    env['PYTHONPATH'] = os.pathsep.join(pythonpath)

    def popen_wait(*args, **kwargs):
        __tracebackhide__ = True

        args = [str(arg) for arg in args]
        kwargs['env'] = dict(env, **kwargs.get('env', {}))

        print('Running', ' '.join(args))
        ret = subprocess.Popen(args, **kwargs).wait()
        assert ret == 0

    return popen_wait


@pytest.fixture
def color(pytestconfig):
    reporter = pytestconfig.pluginmanager.getplugin('terminalreporter')
    try:
        return 'yes' if reporter.writer.hasmarkup else 'no'
    except AttributeError:
        return pytestconfig.option.color


@pytest.fixture
def verbosity(pytestconfig):
    v = pytestconfig.option.verbose or -1
    if v < 0:
        return 'q' * (-v)
    else:
        return 'v' * v


@pytest.fixture
def base_args(bench_dir, verbosity, color):
    return [
        bench_dir,
        '--confcutdir={0}'.format(bench_dir),
        '-x',
        '-{0}'.format(verbosity),
        '-rw',
        '--color={0}'.format(color),
    ]


@pytest.fixture
def bench_args(pytestconfig, storage_dir):
    if pytestconfig.getoption('run_perf') != 'check':
        return [
            '--benchmark-only',
            '--benchmark-disable-gc',
            # '--benchmark-compare',
            '--benchmark-autosave',
            '--benchmark-storage={0}'.format(storage_dir),
        ]
    else:
        return ['--benchmark-disable']


@pytest.fixture
def perf_args(base_args, mode_args, bench_args):
    return base_args + mode_args + bench_args


def test_perf_run(popen, perf_args):
    popen(sys.executable, PYTEST_PATH, *perf_args)
