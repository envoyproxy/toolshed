#!/usr/bin/env bash

set -e -o pipefail

TEST_TEMPDIR=$(mktemp -d)
WATCHER_PID=""
WATCHER_TO_TEST="${1}"
FAILED=0


# This is pretty hacky with a lot of sleeps

if [[ -z "$WATCHER_TO_TEST" ]]; then
    echo "No watcher specified!" >&2
fi

if command -v gdate &> /dev/null; then
    DATE=$(command -v gdate)
else
    DATE=$(command -v date)
fi


_kill_watcher () {
    if [[ -n "$WATCHER_PID" ]]; then
        kill "$WATCHER_PID" &>/dev/null || :
        wait "$WATCHER_PID" &>/dev/null || :
        WATCHER_PID=
    fi
    rm -rf "$TEST_TEMPDIR"
}


_run_log () {
    echo ">> Test: ${1}" >&2
}


# shellcheck disable=SC2317
cleanup () {
    _kill_watcher
    if [[ "$FAILED" -eq 0 ]]; then
        echo "Test complete!"
    else
        echo "Test failed!"
    fi
}

trap cleanup EXIT


_create_test_command () {
    mkdir -p "${TEST_TEMPDIR}"
    cat <<EOF > "${TEST_TEMPDIR}/command.sh"
#!/usr/bin/env bash

sleep .2
$DATE "+%s.%N" >> /tmp/output

EOF
    chmod +x "${TEST_TEMPDIR}/command.sh"
}


_fail () {
    echo "$@" >&2
    cat /tmp/output >&2
    FAILED=1
}


_is_epoch() {
    local regex='^[0-9]{10}\.[0-9]+$'
    [[ $1 =~ $regex ]]
}


_start_watcher () {
    _create_test_command
    rm -rf /tmp/output
    mkdir -p "${TEST_TEMPDIR}/watched"
    for directory in ${TEST_TEMPDIR}/watched/{foo,bar,baz}; do
        mkdir -p "$directory"
        echo "sometext" > "$directory/somefile"
    done
    $WATCHER_TO_TEST "${TEST_TEMPDIR}/watched" "${TEST_TEMPDIR}/command.sh" &
    WATCHER_PID=$!
    sleep .1
}


_test () {
    local line_count
    line_count=$(wc -l < /tmp/output)
    test "$line_count" -eq "${1}" || {
        _fail "Wrong number of lines: expected ${1}, got ${line_count}"
    }
    while IFS= read -r line; do
        _is_epoch "${line}" || echo "Bad line: ${line}"
    done < /tmp/output
}


test_watcher_modify () {
    _run_log modify
    _start_watcher
    echo "othertext" > "${TEST_TEMPDIR}/watched/foo/somefile"
    touch "${TEST_TEMPDIR}/watched/foo/somefile"

    sleep 1.5
    _test 1
    _kill_watcher
}


test_watcher_create () {
    _run_log create
    _start_watcher
    touch "${TEST_TEMPDIR}/watched/otherfile"

    sleep 1.5
    _test 1
    _kill_watcher
}


test_watcher_rm () {
    _run_log rm
    _start_watcher
    rm "${TEST_TEMPDIR}/watched/bar/somefile"

    sleep 1.5
    _test 1
    _kill_watcher
}


test_watcher_mv () {
    _run_log mv
    _start_watcher
    mv "${TEST_TEMPDIR}/watched/baz/somefile" "${TEST_TEMPDIR}/watched/baz/differentfile"
    sleep 1.5
    _test 1
    _kill_watcher
}


_do_multi () {
    echo "BOOM" > "${TEST_TEMPDIR}/watched/baz/newfile"
    sleep .1
    rm "${TEST_TEMPDIR}/watched/baz/somefile"
    sleep .1
    echo "BOOM BOOM" > "${TEST_TEMPDIR}/watched/baz/newfile"
    sleep .1
    echo "BOOM BOOM BOOM" > "${TEST_TEMPDIR}/watched/baz/newfile"
    sleep 1
    echo "BOOM BOOM BOOM BOOM" > "${TEST_TEMPDIR}/watched/baz/newfile"
    sleep 1
    mv "${TEST_TEMPDIR}/watched/baz/newfile" "${TEST_TEMPDIR}/watched/baz/oldfile"
    sleep .1
    rm -rf "${TEST_TEMPDIR}/watched/baz"
}


test_watcher_multi () {
    _run_log multi
    _start_watcher

    _do_multi

    sleep 2

    _test 5
    _kill_watcher
}


runtests () {
    test_watcher_modify
    test_watcher_create
    test_watcher_rm
    test_watcher_mv
    test_watcher_multi
}

runtests
exit "$FAILED"
