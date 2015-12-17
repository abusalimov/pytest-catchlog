import pytest


def test_camel_case_aliases(testdir):
    testdir.makepyfile('''
        import logging

        logger = logging.getLogger(__name__)

        def test_foo(caplog):
            caplog.setLevel(logging.INFO)
            logger.debug('boo!')

            with caplog.atLevel(logging.WARNING):
                logger.info('catch me if you can')
        ''')
    result = testdir.runpytest()
    assert result.ret == 0

    with pytest.raises(pytest.fail.Exception):
        result.stdout.fnmatch_lines(['*- Captured *log call -*'])

    result = testdir.runpytest('-rw')
    assert result.ret == 0
    result.stdout.fnmatch_lines('''
        =*warning summary*=
        *WL1*test_camel_case_aliases*caplog.setLevel()*deprecated*
        *WL1*test_camel_case_aliases*caplog.atLevel()*deprecated*
    ''')


def test_property_call(testdir):
    testdir.makepyfile('''
        import logging

        logger = logging.getLogger(__name__)

        def test_foo(caplog):
            logger.info('boo %s', 'arg')

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
        *WL1*test_property_call*caplog.text()*deprecated*
        *WL1*test_property_call*caplog.records()*deprecated*
        *WL1*test_property_call*caplog.record_tuples()*deprecated*
    ''')
