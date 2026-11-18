"""Tests for a `tap2pcap` binary, on traces of a proto with the fields of Envoy's."""

import os
import subprocess
import sys
import unittest

from google.protobuf import text_format

import pcap
from tap.tests import trace_pb2

TAP2PCAP, TRACE, HTTP_TRACE = sys.argv[1:4]

EXPECTED = [
    dict(
        seconds=1700000000,
        micros=123456,
        src="127.0.0.2",
        sport=53288,
        dst="127.0.0.1",
        dport=10000,
        seq=1,
        ack=1,
        payload=b"GET / HTTP/1.1\r\nhost: example\r\n\r\n"),
    dict(
        seconds=1700000000,
        micros=200000,
        src="127.0.0.1",
        sport=10000,
        dst="127.0.0.2",
        dport=53288,
        seq=1,
        ack=34,
        payload=b"HTTP/1.1 200 OK\r\ncontent-length: 2\r\n\r\n"),
    dict(
        seconds=1700000001,
        micros=0,
        src="127.0.0.1",
        sport=10000,
        dst="127.0.0.2",
        dport=53288,
        seq=39,
        ack=34,
        payload=b"ok"),
]


def run(*args):
    return subprocess.run([TAP2PCAP, *args], capture_output=True, text=True)


class Tap2pcapBinaryTest(unittest.TestCase):

    def assert_converted(self, tap_path, name):
        pcap_path = os.path.join(os.environ["TEST_TMPDIR"], name)
        result = run(tap_path, pcap_path)
        self.assertEqual(result.returncode, 0, result.stderr)
        with open(pcap_path, "rb") as f:
            header, packets = pcap.read_pcap(f.read())
        self.assertEqual(header["linktype"], 1)
        self.assertEqual(
            [{k: packet[k] for k in expected} for packet, expected in zip(packets, EXPECTED)],
            EXPECTED)
        self.assertEqual(len(packets), len(EXPECTED))

    def test_text(self):
        self.assert_converted(TRACE, "text.pcap")

    def test_binary(self):
        wrapper = trace_pb2.TraceWrapper()
        with open(TRACE) as f:
            text_format.Merge(f.read(), wrapper)
        tap_path = os.path.join(os.environ["TEST_TMPDIR"], "socket.pb")
        with open(tap_path, "wb") as f:
            f.write(wrapper.SerializeToString())
        self.assert_converted(tap_path, "binary.pcap")

    def test_not_a_socket_trace(self):
        pcap_path = os.path.join(os.environ["TEST_TMPDIR"], "http.pcap")
        result = run(HTTP_TRACE, pcap_path)
        self.assertEqual(result.returncode, 1)
        self.assertIn("is not a socket buffered trace", result.stderr)
        self.assertFalse(os.path.exists(pcap_path))

    def test_usage(self):
        result = run(TRACE)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usage:", result.stderr)


if __name__ == "__main__":
    unittest.main(argv=sys.argv[:1])
