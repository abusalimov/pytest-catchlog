# -*- coding: utf-8 -*-
import pytest


def test_nothing_logged(testdir):
    testdir.makepyfile('''
        import sys

        def test_foo():
            sys.stdout.write('text going to stdout')
            sys.stderr.write('text going to stderr')
            assert False
        ''')
    result = testdir.runpytest()
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured stdout call -*',
                                 'text going to stdout'])
    result.stdout.fnmatch_lines(['*- Captured stderr call -*',
                                 'text going to stderr'])
    with pytest.raises(pytest.fail.Exception):
        result.stdout.fnmatch_lines(['*- Captured *log call -*'])


def test_messages_logged(testdir):
    testdir.makepyfile('''
        import sys
        import logging

        logger = logging.getLogger(__name__)

        def test_foo():
            sys.stdout.write('text going to stdout')
            sys.stderr.write('text going to stderr')
            logger.info('text going to logger')
            assert False
        ''')
    result = testdir.runpytest()
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured *log call -*',
                                 '*text going to logger*'])
    result.stdout.fnmatch_lines(['*- Captured stdout call -*',
                                 'text going to stdout'])
    result.stdout.fnmatch_lines(['*- Captured stderr call -*',
                                 'text going to stderr'])


def test_setup_logging(testdir):
    testdir.makepyfile('''
        import logging

        logger = logging.getLogger(__name__)

        def setup_function(function):
            logger.info('text going to logger from setup')

        def test_foo():
            logger.info('text going to logger from call')
            assert False
        ''')
    result = testdir.runpytest()
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured *log setup -*',
                                 '*text going to logger from setup*',
                                 '*- Captured *log call -*',
                                 '*text going to logger from call*'])


def test_teardown_logging(testdir):
    testdir.makepyfile('''
        import logging

        logger = logging.getLogger(__name__)

        def test_foo():
            logger.info('text going to logger from call')

        def teardown_function(function):
            logger.info('text going to logger from teardown')
            assert False
        ''')
    result = testdir.runpytest()
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured *log call -*',
                                 '*text going to logger from call*',
                                 '*- Captured *log teardown -*',
                                 '*text going to logger from teardown*'])


def test_disable_log_capturing(testdir):
    testdir.makepyfile('''
        import sys
        import logging

        logger = logging.getLogger(__name__)

        def test_foo():
            sys.stdout.write('text going to stdout')
            logger.warning('catch me if you can!')
            sys.stderr.write('text going to stderr')
            assert False
        ''')
    result = testdir.runpytest('--no-print-logs')
    print(result.stdout)
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured stdout call -*',
                                 'text going to stdout'])
    result.stdout.fnmatch_lines(['*- Captured stderr call -*',
                                 'text going to stderr'])
    with pytest.raises(pytest.fail.Exception):
        result.stdout.fnmatch_lines(['*- Captured *log call -*'])


def test_disable_log_capturing_ini(testdir):
    testdir.makeini(
        '''
        [pytest]
        log_print=False
        '''
    )
    testdir.makepyfile('''
        import sys
        import logging

        logger = logging.getLogger(__name__)

        def test_foo():
            sys.stdout.write('text going to stdout')
            logger.warning('catch me if you can!')
            sys.stderr.write('text going to stderr')
            assert False
        ''')
    result = testdir.runpytest()
    print(result.stdout)
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured stdout call -*',
                                 'text going to stdout'])
    result.stdout.fnmatch_lines(['*- Captured stderr call -*',
                                 'text going to stderr'])
    with pytest.raises(pytest.fail.Exception):
        result.stdout.fnmatch_lines(['*- Captured *log call -*'])


def test_mutable_arg(testdir):
    testdir.makepyfile('''
        import logging

        logger = logging.getLogger(__name__)

        def test_it():
            mutable = {}
            logger.info("Mutable dict %r empty", mutable)
            mutable['foo'] = 'bar'
            logger.info("Mutable dict %r bar", mutable)
            mutable['foo'] = 'baz'
            logger.info("Mutable dict %r baz", mutable)
            assert False
        ''')
    result = testdir.runpytest()
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured *log call -*',
                                 "*Mutable dict {} empty",
                                 "*Mutable dict {'foo': 'bar'} bar",
                                 "*Mutable dict {'foo': 'baz'} baz"])
