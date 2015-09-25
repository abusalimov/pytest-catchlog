# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import logging
from contextlib import closing, contextmanager

import pytest
import py


__version__ = '1.1'


def get_logger_obj(logger=None):
    """Get a logger object that can be specified by its name, or passed as is.

    Defaults to the root logger.
    """
    if logger is None or isinstance(logger, py.builtin._basestring):
        logger = logging.getLogger(logger)
    return logger

@contextmanager
def logging_at_level(level, logger=None):
    """Context manager that sets the level for capturing of logs."""
    logger = get_logger_obj(logger)

    orig_level = logger.level
    logger.setLevel(level)
    try:
        yield
    finally:
        logger.setLevel(orig_level)

@contextmanager
def logging_using_handler(handler, logger=None):
    """Context manager that safely register a given handler."""
    logger = get_logger_obj(logger)

    if handler in logger.handlers:  # reentrancy
        # Adding the same handler twice would confuse logging system.
        # Just don't do that.
        yield
    else:
        logger.addHandler(handler)
        try:
            yield
        finally:
            logger.removeHandler(handler)

@contextmanager
def catching_logs(handler, filter=None, formatter=None,
                  level=logging.NOTSET, logger=None):
    """Context manager that prepares the whole logging machinery properly."""
    logger = get_logger_obj(logger)

    if filter is not None:
        handler.addFilter(filter)
    if formatter is not None:
        handler.setFormatter(formatter)
    handler.setLevel(level)

    with closing(handler), \
            logging_using_handler(handler, logger), \
            logging_at_level(min(handler.level, logger.level), logger):

        yield handler


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
        self.print_logs = config.getoption('log_print')
        self.formatter = logging.Formatter(
                get_option_ini(config, 'log_format'),
                get_option_ini(config, 'log_date_format'))

    def _make_runtest_for(when):
        """Create a hook method for a given context (setup/call/teardown)."""

        @pytest.mark.hookwrapper
        def runtest_func(self, item):
            """Implements pytest_runtest_xxx() hook."""
            with closing(py.io.TextIO()) as stream, \
                    catching_logs(logging.StreamHandler(stream),
                                  formatter=self.formatter):
                yield  # run test

                if self.print_logs:
                    # Add a captured log section to the report.
                    log = stream.getvalue().strip()
                    item.add_report_section(when, 'log', log)

        runtest_func.__name__ = 'pytest_runtest_' + when  # just in case
        return runtest_func

    pytest_runtest_setup    = _make_runtest_for('setup')
    pytest_runtest_call     = _make_runtest_for('call')
    pytest_runtest_teardown = _make_runtest_for('teardown')

    del _make_runtest_for


class RecordingHandler(logging.Handler):
    """A logging handler that stores log records into a buffer."""

    @property
    def records(self):
        """Returns the list of captured records in a thread-safe way."""
        self.acquire()
        try:
            return list(self.buffer)
        finally:
            self.release()

    def __init__(self):
        super(RecordingHandler, self).__init__()
        self.buffer = []

    def emit(self, record):  # Called with the lock acquired.
        self.buffer.append(record)


class CatchLogFuncArg(object):
    """Provides access and control of log capturing."""

    def __init__(self, handler):
        """Creates a new funcarg."""
        self._handler = handler

    def records(self):
        """Returns the list of log records."""
        return self._handler.records

    def record_tuples(self):
        """Returns a list of a striped down version of log records intended
        for use in assertion comparison.

        The format of the tuple is:

            (logger_name, log_level, message)
        """
        return [(r.name, r.levelno, r.getMessage()) for r in self.records()]

    def text(self):
        """Returns the log text."""
        with closing(py.io.TextIO()) as stream:
            stream_handler = logging.StreamHandler(stream)

            for r in self.records():
                stream_handler.handle(r)

            return stream.getvalue()

    def set_level(self, level):
        """Sets the level for recording of logs.

        This only affects logs collected by this recorder. To control all
        captured logs, including these reported for failed tests, use the
        ``caplog.set_logging_level()`` method instead.
        """
        self._handler.setLevel(level)

    def at_level(self, level):
        """Context manager that controls the level for recording of logs.

        This only affects logs collected by this recorder. To control all
        captured logs, including these reported for failed tests, use the
        ``caplog.logging_at_level()`` context manager instead.
        """
        return logging_at_level(level, self._handler)  # duck typing: quack!

    # Helper methods controlling a level of the global logging.

    @staticmethod
    def set_logging_level(level, logger=None):
        """Sets the level for the logging subsystem.

        By default, the level is set on the root logger aggregating all logs.
        Specify a logger or its name to instead set the level of any logger.
        """
        get_logger_obj(logger).setLevel(level)

    @staticmethod
    def logging_at_level(level, logger=None):
        """Context manager that sets the level for the logging subsystem.

        By default, the level is set on the root logger aggregating all logs.
        Specify a logger or its name to instead set the level of any logger.
        """
        return logging_at_level(level, logger)


@pytest.yield_fixture
def caplog(request):
    """Access and control log capturing and recording."""
    with catching_logs(RecordingHandler()) as handler:
        yield CatchLogFuncArg(handler)


capturelog = caplog
