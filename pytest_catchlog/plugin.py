# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import logging
import sys
from contextlib import closing, contextmanager

import pytest
import py

from pytest_catchlog.common import catching_logs

# Let the fixtures be discoverable by pytest.
from pytest_catchlog.fixture import caplog, capturelog


DEFAULT_LOG_FORMAT = '%(filename)-25s %(lineno)4d %(levelname)-8s %(message)s'
DEFAULT_DATE_FORMAT = '%H:%M:%S'


def add_option_ini(parser, option, dest,
                   type=None, action=None, default=None, help=None):
    parser.addini(dest, default=default, type=type,
                  help='default value for ' + option)
    parser.getgroup('catchlog').addoption(option,
                                          dest=dest, action=action, help=help)


def get_option_ini(config, name):
    ret = config.getoption(name)  # 'default' arg won't work as expected
    if ret is None:
        ret = config.getini(name)
    return ret


def pytest_addoption(parser):
    """Add options to control log capturing."""

    group = parser.getgroup('catchlog', 'Log catching')
    group.addoption(
        '--no-print-logs',
        dest='log_print', action='store_false', default=True,
        help='disable printing caught logs on failed tests.'
    )
    add_option_ini(parser,
        '--log-format',
        dest='log_format',
        default=DEFAULT_LOG_FORMAT,
        help='log format as used by the logging module.'
    )
    add_option_ini(parser,
        '--log-date-format',
        dest='log_date_format',
        default=DEFAULT_DATE_FORMAT,
        help='log date format as used by the logging module.'
    )
    add_option_ini(parser,
        '--log-level-extra',
        dest='log_level_extra',
        type='args',
        action='append',
        help='extra logging levels that verbosity should be sensible to.'
    )


def pytest_configure(config):
    """Always register the log catcher plugin with py.test or tests can't
    find the  fixture function.
    """
    # Prepare the available levels dictionary
    available_levels = set([
        logging.CRITICAL,
        logging.ERROR,
        logging.WARNING,
        logging.INFO,
        logging.DEBUG,
        logging.NOTSET
    ])
    for level in get_option_ini(config, 'log_level_extra'):
        try:
            level_num = int(getattr(logging, level, level))
        except ValueError:
            # Python logging does not recognise this as a logging level
            raise pytest.UsageError(
                "'{0}' is not recognized as a logging level name. Please "
                "consider passing the logging level num instead.".format(
                    level))
        else:
            if not (logging.NOTSET <= level_num <= logging.CRITICAL):
                raise pytest.UsageError(
                    "'{0}' is ignored as not being in the valid logging "
                    "levels range: NOTSET({1}) - CRITICAL({2})".format(
                        level,
                        logging.NOTSET,
                        logging.CRITICAL))

        available_levels.add(level_num)

    # Build a dictionary mapping of verbosity level to logging level, as
    # follows, unless there's custom levels added
    # verbosity=0         CRITICAL (no pytest output is shown and CRITICAL
    #                               log messages are displayd)
    # verbosity=1   -v    ERROR    (pytest verbosity kicks in, but only
    #                               log messages with higher or equal
    #                               level to ERROR are shown)
    # verbosity=2   -vv   WARNING  (start showing log messages with a
    #                               higher or equal level to WARNING)
    # verbosity=4   -vvv  INFO
    # - ... etc
    handled_levels = dict(enumerate(sorted(available_levels, reverse=True)))

    # Set the console verbosity level
    verbosity = config.getoption('-v')
    min_verbosity = min(handled_levels)
    max_verbosity = max(handled_levels)
    if verbosity in handled_levels:
        cli_handler_level = handled_levels[verbosity]
    elif verbosity >= max_verbosity:
        cli_handler_level = handled_levels[max_verbosity]
    else:
        cli_handler_level = handled_levels[min_verbosity]

    config._catch_log_cli_handler_level = cli_handler_level
    config.pluginmanager.register(CatchLogPlugin(config), '_catch_log')


class CatchLogPlugin(object):
    """Attaches to the logging module and captures log messages for each test.
    """

    def __init__(self, config):
        """Creates a new plugin to capture log messages.

        The formatter can be safely shared across all handlers so
        create a single one for the entire test session here.
        """
        self.print_logs = config.getoption('log_print')
        self.formatter = logging.Formatter(
                get_option_ini(config, 'log_format'),
                get_option_ini(config, 'log_date_format'))
        self.handler = logging.StreamHandler(sys.stderr)
        self.handler.setFormatter(self.formatter)

    @contextmanager
    def _runtest_for(self, item, when):
        """Implements the internals of pytest_runtest_xxx() hook."""
        with catching_logs(LogCaptureHandler(),
                           formatter=self.formatter) as log_handler:
            item.catch_log_handler = log_handler
            try:
                yield  # run test
            finally:
                del item.catch_log_handler

            if self.print_logs:
                # Add a captured log section to the report.
                log = log_handler.stream.getvalue().strip()
                item.add_report_section(when, 'log', log)

    @pytest.mark.hookwrapper
    def pytest_runtest_setup(self, item):
        with self._runtest_for(item, 'setup'):
            yield

    @pytest.mark.hookwrapper
    def pytest_runtest_call(self, item):
        with self._runtest_for(item, 'call'):
            yield

    @pytest.mark.hookwrapper
    def pytest_runtest_teardown(self, item):
        with self._runtest_for(item, 'teardown'):
            yield

    @pytest.mark.hookwrapper
    def pytest_runtestloop(self, session):
        """Runs all collected test items."""
        with catching_logs(self.handler,
                           level=session.config._catch_log_cli_handler_level):
            yield  # run all the tests


class LogCaptureHandler(logging.StreamHandler):
    """A logging handler that stores log records and the log text."""

    def __init__(self):
        """Creates a new log handler."""

        logging.StreamHandler.__init__(self)
        self.stream = py.io.TextIO()
        self.records = []

    def close(self):
        """Close this log handler and its underlying stream."""

        logging.StreamHandler.close(self)
        self.stream.close()

    def emit(self, record):
        """Keep the log records in a list in addition to the log text."""

        self.records.append(record)
        logging.StreamHandler.emit(self, record)
