# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import functools
import logging

import pytest

from pytest_catchlog.common import catching_logs, logging_at_level


class RecordingHandler(logging.Handler, object):  # Python 2.6: new-style class
    """A logging handler that stores log records into a buffer."""

    def __init__(self):
        super(RecordingHandler, self).__init__()
        self.records = []

    def emit(self, record):  # Called with the lock acquired.
        self.records.append(record)


class LogCaptureFixture(object):
    """Provides access and control of log capturing."""

    def __init__(self, handler):
        """Creates a new funcarg."""
        super(LogCaptureFixture, self).__init__()
        self.handler = handler

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

    @property
    def text(self):
        """Returns the log text."""
        record_fmt = logging.BASIC_FORMAT + '\n'  # always the standard format
        return ''.join(record_fmt % r.__dict__ for r in self.records)

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
            ret = cls(func(self))
            ret._warn_compat = self._warn_compat
            ret._prop_name = func.__name__
            return ret

        return make_property(getter)

    def __call__(self):
        self._warn_compat(old="'caplog.{0}()' syntax".format(self._prop_name),
                          new="'caplog.{0}' property".format(self._prop_name))
        return self


class CallableList(CallablePropertyMixin, list):
    pass


class CallableStr(CallablePropertyMixin, str):
    pass


class CompatLogCaptureFixture(LogCaptureFixture):
    """Backward compatibility with pytest-capturelog."""

    def __init__(self, handler, item):
        """Creates a new funcarg."""
        super(CompatLogCaptureFixture, self).__init__(handler)
        self._item = item

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


@pytest.yield_fixture
def caplog(request):
    """Access and control log capturing.

    Captured logs are available through the following methods::

    * caplog.text()          -> string containing formatted log output
    * caplog.records()       -> list of logging.LogRecord instances
    * caplog.record_tuples() -> list of (logger_name, level, message) tuples
    """
    with catching_logs(RecordingHandler()) as handler:
        yield CompatLogCaptureFixture(handler, item=request.node)


capturelog = caplog
