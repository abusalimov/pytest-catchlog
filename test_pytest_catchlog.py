import os
import textwrap
import py

pytest_plugins = 'pytester'


def test_nothing_logged(testdir):
    testdir.makepyfile('''
        import sys
        import logging

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
    py.test.raises(Exception, result.stdout.fnmatch_lines,
                   ['*- Captured *log call -*'])


def test_messages_logged(testdir):
    testdir.makepyfile('''
        import sys
        import logging

        def test_foo():
            sys.stdout.write('text going to stdout')
            sys.stderr.write('text going to stderr')
            logging.getLogger().info('text going to logger')
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
        import sys
        import logging

        def setup_function(function):
            logging.getLogger().info('text going to logger from setup')

        def test_foo():
            logging.getLogger().info('text going to logger from call')
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
        import sys
        import logging

        def test_foo():
            logging.getLogger().info('text going to logger from call')

        def teardown_function(function):
            logging.getLogger().info('text going to logger from teardown')
            assert False
        ''')
    result = testdir.runpytest()
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured *log call -*',
                                 '*text going to logger from call*',
                                 '*- Captured *log teardown -*',
                                 '*text going to logger from teardown*'])


def test_change_level(testdir):
    testdir.makepyfile('''
        import sys
        import logging

        def test_foo(caplog):
            caplog.set_level(logging.INFO)
            log = logging.getLogger()
            log.debug('handler DEBUG level')
            log.info('handler INFO level')

            caplog.set_level(logging.CRITICAL, logger='root.baz')
            log = logging.getLogger('root.baz')
            log.warning('logger WARNING level')
            log.critical('logger CRITICAL level')

            assert False
        ''')
    result = testdir.runpytest()
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured *log call -*',
                                 '*handler INFO level*',
                                 '*logger CRITICAL level*'])
    py.test.raises(Exception, result.stdout.fnmatch_lines,
                   ['*- Captured *log call -*', '*handler DEBUG level*'])
    py.test.raises(Exception, result.stdout.fnmatch_lines,
                   ['*- Captured *log call -*', '*logger WARNING level*'])


@py.test.mark.skipif('sys.version_info < (2,5)')
def test_with_statement(testdir):
    testdir.makepyfile('''
        from __future__ import with_statement
        import sys
        import logging

        def test_foo(caplog):
            with caplog.at_level(logging.INFO):
                log = logging.getLogger()
                log.debug('handler DEBUG level')
                log.info('handler INFO level')

                with caplog.at_level(logging.CRITICAL, logger='root.baz'):
                    log = logging.getLogger('root.baz')
                    log.warning('logger WARNING level')
                    log.critical('logger CRITICAL level')

            assert False
        ''')
    result = testdir.runpytest()
    assert result.ret == 1
    result.stdout.fnmatch_lines(['*- Captured *log call -*',
                                 '*handler INFO level*',
                                 '*logger CRITICAL level*'])
    py.test.raises(Exception, result.stdout.fnmatch_lines,
                   ['*- Captured *log call -*', '*handler DEBUG level*'])
    py.test.raises(Exception, result.stdout.fnmatch_lines,
                   ['*- Captured *log call -*', '*logger WARNING level*'])


def test_log_access(testdir):
    testdir.makepyfile('''
        import sys
        import logging

        def test_foo(caplog):
            logging.getLogger().info('boo %s', 'arg')
            assert caplog.records[0].levelname == 'INFO'
            assert caplog.records[0].msg == 'boo %s'
            assert 'boo arg' in caplog.text
        ''')
    result = testdir.runpytest()
    assert result.ret == 0


def test_funcarg_help(testdir):
    result = testdir.runpytest('--funcargs')
    result.stdout.fnmatch_lines(['*caplog*'])


def test_record_tuples(testdir):
    testdir.makepyfile('''
        import sys
        import logging

        def test_foo(caplog):
            logging.getLogger().info('boo %s', 'arg')

            assert caplog.record_tuples == [
                ('root', logging.INFO, 'boo arg'),
            ]
        ''')
    result = testdir.runpytest()
    assert result.ret == 0


def test_compat_camel_case_aliases(testdir):
    testdir.makepyfile('''
        import logging

        def test_foo(caplog):
            caplog.setLevel(logging.INFO)
            logging.getLogger().debug('boo!')

            with caplog.atLevel(logging.WARNING):
                logging.getLogger().info('catch me if you can')
        ''')
    result = testdir.runpytest()
    assert result.ret == 0

    py.test.raises(Exception, result.stdout.fnmatch_lines,
                   ['*- Captured *log call -*'])

    result = testdir.runpytest('-rw')
    assert result.ret == 0
    result.stdout.fnmatch_lines('''
        =*warning summary*=
        *WL1*test_compat_camel_case_aliases*caplog.setLevel()*deprecated*
        *WL1*test_compat_camel_case_aliases*caplog.atLevel()*deprecated*
    ''')


def test_compat_properties(testdir):
    testdir.makepyfile('''
        import logging

        def test_foo(caplog):
            logging.getLogger().info('boo %s', 'arg')

            assert caplog.text    == caplog.text()    == str(caplog.text)
            assert caplog.records == caplog.records() == list(caplog.records)
            assert (caplog.record_tuples ==
                    caplog.record_tuples() == list(caplog.record_tuples))
        ''')
    result = testdir.runpytest()
    assert result.ret == 0

    result = testdir.runpytest('-rw')
    assert result.ret == 0
    result.stdout.fnmatch_lines('''
        =*warning summary*=
        *WL1*test_compat_properties*caplog.text()*deprecated*
        *WL1*test_compat_properties*caplog.records()*deprecated*
        *WL1*test_compat_properties*caplog.record_tuples()*deprecated*
    ''')


def test_compat_records_modification(testdir):
    testdir.makepyfile('''
        import logging

        logger = logging.getLogger()

        def test_foo(caplog):
            logger.info('boo %s', 'arg')
            assert caplog.records
            assert caplog.records()

            del caplog.records()[:]  # legacy syntax
            assert not caplog.records
            assert not caplog.records()

            logger.info('foo %s', 'arg')
            assert caplog.records
            assert caplog.records()
        ''')
    result = testdir.runpytest()
    assert result.ret == 0


def test_disable_log_capturing(testdir):
    testdir.makepyfile('''
        import sys
        import logging

        def test_foo(caplog):
            sys.stdout.write('text going to stdout')
            logging.getLogger().warning('catch me if you can!')
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
    py.test.raises(Exception, result.stdout.fnmatch_lines,
                   ['*- Captured *log call -*'])


def test_logging_level_fatal(testdir):
    testdir.makepyfile('''
        import pytest
        import logging

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.FATAL
            print('PASSED')

    ''')

    result = testdir.runpytest('-s')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'test_logging_level_fatal.py PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_critical(testdir):
    testdir.makepyfile('''
        import pytest
        import logging

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.CRITICAL
    ''')

    result = testdir.runpytest('-v')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_error(testdir):
    testdir.makepyfile('''
        import pytest
        import logging

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.ERROR
    ''')

    result = testdir.runpytest('-vv')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_warning(testdir):
    testdir.makepyfile('''
        import pytest
        import logging

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.WARNING
    ''')

    result = testdir.runpytest('-vvv')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_info(testdir):
    testdir.makepyfile('''
        import pytest
        import logging

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.INFO
    ''')

    result = testdir.runpytest('-vv', '-vv')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_debug(testdir):
    testdir.makepyfile('''
        import pytest
        import logging

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.DEBUG
    ''')

    result = testdir.runpytest('-vv', '-vvv')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_trace(testdir):
    with open(os.path.join(testdir.tmpdir.strpath, 'conftest.py'), 'w') as wfh:
        wfh.write(textwrap.dedent('''
            def pytest_configure(config):
                config.addinivalue_line('log_extra_levels', '5')
        '''))
    testdir.makepyfile('''
        import pytest
        import logging

        if not hasattr(logging, 'TRACE'):
            logging.TRACE = 5
            logging.addLevelName(logging.TRACE, 'TRACE')

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.TRACE
    ''')

    result = testdir.runpytest('-vvvvvv')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_trace_cli(testdir):
    testdir.makepyfile('''
        import pytest
        import logging

        if not hasattr(logging, 'TRACE'):
            logging.TRACE = 5
            logging.addLevelName(logging.TRACE, 'TRACE')

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.TRACE
    ''')

    result = testdir.runpytest('-vvvvvv', '--log-extra-level=5')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_garbage(testdir):
    with open(os.path.join(testdir.tmpdir.strpath, 'conftest.py'), 'w') as wfh:
        wfh.write(textwrap.dedent('''
            def pytest_configure(config):
                config.addinivalue_line('log_extra_levels', '5')
                config.addinivalue_line('log_extra_levels', '1')
        '''))
    testdir.makepyfile('''
        import pytest
        import logging

        if not hasattr(logging, 'GARBAGE'):
            logging.GARBAGE = 1
            logging.addLevelName(logging.GARBAGE, 'GARBAGE')

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.GARBAGE
    ''')

    result = testdir.runpytest('-vvvvvvv')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_garbage_cli(testdir):
    testdir.makepyfile('''
        import pytest
        import logging

        if not hasattr(logging, 'GARBAGE'):
            logging.GARBAGE = 1
            logging.addLevelName(logging.GARBAGE, 'GARBAGE')

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.GARBAGE
    ''')

    result = testdir.runpytest('-vvvvvvv',
                               '--log-extra-level=5',
                               '--log-extra-level=1')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_not_set(testdir):
    with open(os.path.join(testdir.tmpdir.strpath, 'conftest.py'), 'w') as wfh:
        wfh.write(textwrap.dedent('''
            def pytest_configure(config):
                config.addinivalue_line('log_extra_levels', '5')
                config.addinivalue_line('log_extra_levels', '1')
        '''))
    testdir.makepyfile('''
        import pytest
        import logging

        if not hasattr(logging, 'TRACE'):
            logging.TRACE = 5
            logging.addLevelName(logging.TRACE, 'TRACE')
        if not hasattr(logging, 'GARBAGE'):
            logging.GARBAGE = 1
            logging.addLevelName(logging.GARBAGE, 'GARBAGE')

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.NOTSET
    ''')

    for idx in range(8, 11):
        result = testdir.runpytest('-' + 'v'*idx)

        # fnmatch_lines does an assertion internally
        result.stdout.fnmatch_lines([
            '*::test_logging_level PASSED',
        ])

        # make sure that that we get a '0' exit code for the testsuite
        assert result.ret == 0


def test_logging_level_not_set_cli(testdir):
    testdir.makepyfile('''
        import pytest
        import logging

        if not hasattr(logging, 'TRACE'):
            logging.TRACE = 5
            logging.addLevelName(logging.TRACE, 'TRACE')
        if not hasattr(logging, 'GARBAGE'):
            logging.GARBAGE = 1
            logging.addLevelName(logging.GARBAGE, 'GARBAGE')

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.NOTSET
    ''')

    for idx in range(8, 11):
        result = testdir.runpytest('-' + 'v'*idx,
                                   '--log-extra-level=5',
                                   '--log-extra-level=1')

        # fnmatch_lines does an assertion internally
        result.stdout.fnmatch_lines([
            '*::test_logging_level PASSED',
        ])

        # make sure that that we get a '0' exit code for the testsuite
        assert result.ret == 0


def test_unknown_log_level_name(testdir):
    testdir.makepyfile('''
        def test_unknown_log_level():
            pass
    ''')

    result = testdir.runpytest('-vvvvvv', '--log-extra-level=NOTSETS')
    result.stderr.fnmatch_lines([
        "*ERROR: 'NOTSETS' is not recognized as a logging level name.*",
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret != 0
