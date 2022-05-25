

def test_abstracts_fixture(testdir):
    """Make sure that pytest accepts our fixture."""

    # create a temporary pytest test module
    testdir.makepyfile("""
        def test_sth(abstracts):
            assert str(abstracts).startswith("<function _abstracts at")
    """)

    # run pytest with the following cmd args
    result = testdir.runpytest("-v")

    # fnmatch_lines does an assertion internally
    result.stdout.fnmatch_lines([
        '*::test_sth PASSED*',
    ])

    # make sure that that we get a '0' exit code for the testsuite
    assert result.ret == 0
