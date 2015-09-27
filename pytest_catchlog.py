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

    @pytest.mark.hookwrapper
    def pytest_runtest_call(self, item):
        with catching_logs(CatchLogHandler()) as log_handler:
            item.catch_log_handler = log_handler
            try:
                yield  # run test
            finally:
                del item.catch_log_handler

            if self.print_logs:
                # Add a captured log section to the report.
                log = log_handler.stream.getvalue().strip()
                item.add_report_section('call', 'log', log)


class CatchLogHandler(logging.StreamHandler):
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


class CatchLogFuncArg(object):
    """Provides access and control of log capturing."""

    def __init__(self, handler):
        """Creates a new funcarg."""

        self.handler = handler

    def text(self):
        """Returns the log text."""

        return self.handler.stream.getvalue()

    def records(self):
        """Returns the list of log records."""

        return self.handler.records

    def record_tuples(self):
        """Returns a list of a striped down version of log records intended
        for use in assertion comparison.

        The format of the tuple is:

            (logger_name, log_level, message)
        """
        return [(r.name, r.levelno, r.getMessage()) for r in self.records()]

    def set_level(self, level, logger=None):
        """Sets the level for capturing of logs.

        By default, the level is set on the handler used to capture
        logs. Specify a logger name to instead set the level of any
        logger.
        """

        obj = logger and logging.getLogger(logger) or self.handler
        obj.setLevel(level)

    def at_level(self, level, logger=None):
        """Context manager that sets the level for capturing of logs.

        By default, the level is set on the handler used to capture
        logs. Specify a logger name to instead set the level of any
        logger.
        """

        obj = logger and logging.getLogger(logger) or self.handler
        return logging_at_level(level, obj)


def pytest_funcarg__caplog(request):
    """Returns a funcarg to access and control log capturing."""

    return CatchLogFuncArg(request._pyfuncitem.catch_log_handler)


def pytest_funcarg__capturelog(request):
    """Returns a funcarg to access and control log capturing."""

    return CatchLogFuncArg(request._pyfuncitem.catch_log_handler)
