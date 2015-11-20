# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import logging
from contextlib import closing, contextmanager

import pytest
import py

from pytest_catchlog.common import catching_logs

# Let the fixtures be discoverable by pytest.
from pytest_catchlog.fixture import caplog, capturelog


def add_option_ini(parser, option, dest, default=None, help=None):
    parser.addini(dest, default=default,
                  help='default value for ' + option)
    parser.getgroup('catchlog').addoption(option, dest=dest, help=help)


def get_option_ini(config, name):
    ret = config.getoption(name)  # 'default' arg won't work as expected
    if ret is None:
        ret = config.getini(name)
    return ret


def pytest_addoption(parser):
    """Add options to control log capturing."""

    group = parser.getgroup('catchlog', 'Log catching')
    group.addoption('--no-print-logs',
                    dest='log_print', action='store_false', default=True,
                    help='disable printing caught logs on failed tests.')
    add_option_ini(parser,
                   '--log-format',
                   dest='log_format', default=('%(filename)-25s %(lineno)4d'
                                               ' %(levelname)-8s %(message)s'),
                   help='log format as used by the logging module.')
    add_option_ini(parser,
                   '--log-date-format',
                   dest='log_date_format', default=None,
                   help='log date format as used by the logging module.')


def pytest_configure(config):
    """Always register the log catcher plugin with py.test or tests can't
    find the  fixture function.
    """
    config.pluginmanager.register(CatchLogPlugin(config), '_catch_log')


class CatchLogPlugin(object):
    """Attaches to the logging module and captures log messages for each test.
    """

    def __init__(self, config):
        """Creates a new plugin to capture log messages.

        The formatter can be safely shared across all handlers so
        create a single one for the entire test session here.
        """
        self.capture_logs = (config.getoption('capture', 'no') != 'no')
        self.print_logs = config.getoption('log_print')
        self.formatter = logging.Formatter(
                get_option_ini(config, 'log_format'),
                get_option_ini(config, 'log_date_format'))

        handler = logging.StreamHandler()  # streams to stderr by default
        handler.setFormatter(self.formatter)

        self.handler = handler

    @pytest.mark.hookwrapper
    def pytest_runtestloop(self, session):
        """Runs all collected test items."""
        with catching_logs(self.handler):
            yield  # run all the tests

    @contextmanager
    def _runtest_for(self, item, when):
        """Implements the internals of pytest_runtest_xxx() hook."""
        if not self.capture_logs:
            yield
            return
        with closing(py.io.TextIO()) as stream:
            orig_stream = self.handler.stream
            self.handler.stream = stream
            try:
                yield  # run test
            finally:
                self.handler.stream = orig_stream

            if self.print_logs:
                # Add a captured log section to the report.
                log = stream.getvalue().strip()
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
