# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import functools
import logging
import sys
from contextlib import closing, contextmanager

import pytest
import py


__version__ = '1.2.1'


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

    with closing(handler):
        with logging_using_handler(handler, logger):
            with logging_at_level(min(handler.level, logger.level), logger):

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
                   dest='log_format',
                   default=CatchLogPlugin.DEFAULT_LOG_FORMAT,
                   help='log format as used by the logging module.')
    add_option_ini(parser,
                   '--log-date-format',
                   dest='log_date_format',
                   default=CatchLogPlugin.DEFAULT_DATE_FORMAT,
                   help='log date format as used by the logging module.')


def pytest_configure(config):
    """Always register the log catcher plugin with py.test or tests can't
    find the  fixture function.
    """
    config.pluginmanager.register(CatchLogPlugin(config), '_catch_log')


class CatchLogPlugin(object):
    """Attaches to the logging module and captures log messages for each test.
    """
    DEFAULT_LOG_FORMAT = '%(filename)-25s %(lineno)4d %(levelname)-8s %(message)s'
    DEFAULT_DATE_FORMAT = '%H:%M:%S'

    def __init__(self, config):
        """Creates a new plugin to capture log messages.

        The formatter can be safely shared across all handlers so
        create a single one for the entire test session here.
        """
        self.print_logs = config.getoption('log_print')
        self.formatter = logging.Formatter(
                get_option_ini(config, 'log_format'),
                get_option_ini(config, 'log_date_format'))
        terminal = py.io.TerminalWriter(sys.stderr)  # pylint: disable=no-member
        self.console = logging.StreamHandler(terminal)
        self.console.setFormatter(self.formatter)
        # Add the handler to logging
        logging.root.addHandler(self.console)
        # The root logging should have the lowest logging level to allow all
        # messages to be "passed" to the handlers
        logging.root.setLevel(logging.NOTSET)
        self.configure_console_handler(config.getoption('-v'))

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

    def configure_console_handler(self, verbosity):
        # Prepare the handled_levels dictionary
        log_levels = []
        handled_levels = {}
        try:
            available_levels = logging._levelNames.keys()
        except AttributeError:
            # Python >= 3.4
            # And also PyPy3-2.4.0(Python 3.2) apparently...
            # https://travis-ci.org/eisensheng/pytest-catchlog/jobs/91417631
            available_levels = logging._levelToName.keys()
        for level in available_levels:
            if not isinstance(level, int):
                # This is the log level name, not the log level num
                continue
            if level > logging.WARN:
                # -v set's the console handler logging level to ERROR, higher
                # log level messages, ie, >= FATAL are always shown
                continue
            if level <= logging.NOTSET:
                # Log levels lower than NOTSET, inclusive, we're not interested
                continue
            if level in log_levels:
                # We already know about this log level
                continue
            log_levels.append(level)

        # Reverse the list because we're interested on higher logging levels
        # first
        log_levels = sorted(log_levels, reverse=True)

        # Build a dictionary mapping of verbosity level to logging level
        # -v    WARN
        # -vv   INFO
        # -vvv  DEBUG
        # - ... etc
        for idx, level in enumerate(log_levels):
            handled_levels[idx + 2] = level

        # Set the console verbosity level
        min_verbosity = 2  # -v  - WARN loggin level
        max_verbosity = len(handled_levels) + 1
        if verbosity > 1:
            if verbosity in handled_levels:
                log_level = handled_levels[verbosity]
            elif verbosity >= max_verbosity:
                log_level = handled_levels[max_verbosity]
            else:
                log_level = handled_levels[min_verbosity]
            self.console.setLevel(log_level)
        else:
            # The console handler defaults to the highest logging level
            self.console.setLevel(logging.FATAL)


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


class LogCaptureFixture(object):
    """Provides access and control of log capturing."""

    @property
    def handler(self):
        return self._item.catch_log_handler

    def __init__(self, item):
        """Creates a new funcarg."""
        self._item = item

    @property
    def text(self):
        """Returns the log text."""
        return self.handler.stream.getvalue()

    @property
    def records(self):
        """Returns the list of log records."""
        return self.handler.records

    @property
    def record_tuples(self):
        """Returns a list of a striped down version of log records intended
        for use in assertion comparison.

        The format of the tuple is:

            (logger_name, log_level, message)
        """
        return [(r.name, r.levelno, r.getMessage()) for r in self.records]

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


class CallablePropertyMixin(object):
    """Backward compatibility for functions that became properties."""

    @classmethod
    def compat_property(cls, func):
        if isinstance(func, property):
            make_property = func.getter
            func = func.fget
        else:
            make_property = property

        @functools.wraps(func)
        def getter(self):
            naked_value = func(self)
            ret = cls(naked_value)
            ret._naked_value = naked_value
            ret._warn_compat = self._warn_compat
            ret._prop_name = func.__name__
            return ret

        return make_property(getter)

    def __call__(self):
        self._warn_compat(old="'caplog.{0}()' syntax".format(self._prop_name),
                          new="'caplog.{0}' property".format(self._prop_name))
        return self._naked_value  # to let legacy clients modify the object


class CallableList(CallablePropertyMixin, list):
    pass


class CallableStr(CallablePropertyMixin, str):
    pass


class CompatLogCaptureFixture(LogCaptureFixture):
    """Backward compatibility with pytest-capturelog."""

    def _warn_compat(self, old, new):
        self._item.warn(code='L1',
                        message=("{0} is deprecated, use {1} instead"
                                 .format(old, new)))

    @CallableStr.compat_property
    def text(self):
        return super(CompatLogCaptureFixture, self).text

    @CallableList.compat_property
    def records(self):
        return super(CompatLogCaptureFixture, self).records

    @CallableList.compat_property
    def record_tuples(self):
        return super(CompatLogCaptureFixture, self).record_tuples

    def setLevel(self, level, logger=None):
        self._warn_compat(old="'caplog.setLevel()'",
                          new="'caplog.set_level()'")
        return self.set_level(level, logger)

    def atLevel(self, level, logger=None):
        self._warn_compat(old="'caplog.atLevel()'",
                          new="'caplog.at_level()'")
        return self.at_level(level, logger)


@pytest.fixture
def caplog(request):
    """Access and control log capturing.

    Captured logs are available through the following methods::

    * caplog.text()          -> string containing formatted log output
    * caplog.records()       -> list of logging.LogRecord instances
    * caplog.record_tuples() -> list of (logger_name, level, message) tuples
    """
    return CompatLogCaptureFixture(request.node)

capturelog = caplog
