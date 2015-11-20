import logging


def test_logging_level_critical(testdir):
    testdir.makepyfile('''
        import logging

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.CRITICAL
            print('PASSED')

    ''')

    result = testdir.runpytest('-s')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        'test_logging_level_critical.py PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_error(testdir):
    testdir.makepyfile('''
        import logging

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.ERROR
    ''')

    result = testdir.runpytest('-v')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_warning(testdir):
    testdir.makepyfile('''
        import logging

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.WARNING
    ''')

    result = testdir.runpytest('-vv')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_info(testdir):
    testdir.makepyfile('''
        import logging

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.INFO
    ''')

    result = testdir.runpytest('-vv', '-v')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_debug(testdir):
    testdir.makepyfile('''
        import logging

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.DEBUG
    ''')

    result = testdir.runpytest('-vv', '-vv')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_trace(testdir):
    testdir.makeconftest('''
        def pytest_configure(config):
            config.addinivalue_line('log_level_extra', '5')
    ''')
    testdir.makepyfile('''
        import logging

        if not hasattr(logging, 'TRACE'):
            logging.TRACE = 5
            logging.addLevelName(logging.TRACE, 'TRACE')

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.TRACE
    ''')

    result = testdir.runpytest('-vvvvv')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_trace_cli(testdir):
    testdir.makepyfile('''
        import logging

        if not hasattr(logging, 'TRACE'):
            logging.TRACE = 5
            logging.addLevelName(logging.TRACE, 'TRACE')

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.TRACE
    ''')

    result = testdir.runpytest('-vvvvv', '--log-level-extra=5')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_garbage(testdir):
    testdir.makeconftest('''
        def pytest_configure(config):
            config.addinivalue_line('log_level_extra', '5')
            config.addinivalue_line('log_level_extra', '1')
    ''')
    testdir.makepyfile('''
        import logging

        if not hasattr(logging, 'GARBAGE'):
            logging.GARBAGE = 1
            logging.addLevelName(logging.GARBAGE, 'GARBAGE')

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.GARBAGE
    ''')

    result = testdir.runpytest('-vvvvvv')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_garbage_cli(testdir):
    testdir.makepyfile('''
        import logging

        if not hasattr(logging, 'GARBAGE'):
            logging.GARBAGE = 1
            logging.addLevelName(logging.GARBAGE, 'GARBAGE')

        def test_logging_level(request):
            plugin = request.config.pluginmanager.getplugin('_catch_log')
            assert plugin.handler.level == logging.GARBAGE
    ''')

    result = testdir.runpytest('-vvvvvv',
                               '--log-level-extra=5',
                               '--log-level-extra=1')

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_logging_level PASSED',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0


def test_logging_level_not_set(testdir):
    testdir.makeconftest('''
        def pytest_configure(config):
            config.addinivalue_line('log_level_extra', '5')
            config.addinivalue_line('log_level_extra', '1')
    ''')
    testdir.makepyfile('''
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

    for idx in range(7, 10):
        result = testdir.runpytest('-' + 'v'*idx)

        # fnmatch_lines does an assertion internally
        result.stdout.fnmatch_lines([
            '*::test_logging_level PASSED',
        ])

        # make sure that that we get a '0' exit code for the testsuite
        assert result.ret == 0


def test_logging_level_not_set_cli(testdir):
    testdir.makepyfile('''
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
                                   '--log-level-extra=5',
                                   '--log-level-extra=1')

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

    result = testdir.runpytest('-vvvvvv', '--log-level-extra=NOTSETS')
    result.stderr.fnmatch_lines([
        "*ERROR: 'NOTSETS' is not recognized as a logging level name.*",
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret != 0


def test_out_of_range_log_level(testdir):
    testdir.makepyfile('''
        def test_out_of_range_log_level():
            pass
    ''')

    result = testdir.runpytest('-v', '--log-level-extra={0}'
                               .format(logging.CRITICAL+1))
    result.stderr.fnmatch_lines([
        "ERROR: '*' is ignored as not being in the valid logging levels "
        "range: NOTSET* - CRITICAL*"
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret != 0
