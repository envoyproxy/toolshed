"""Tests for the PCAP that `tap2pcap` synthesizes, with no trace proto."""

import io
import unittest

import pcap
import tap2pcap


def convert(connection, events):
    out = io.BytesIO()
    count = tap2pcap.write_pcap(out, connection, events)
    header, packets = pcap.read_pcap(out.getvalue())
    assert count == len(packets)
    return header, packets


class Tap2pcapTest(unittest.TestCase):

    def test_checksum(self):
        # The example of RFC 1071.
        self.assertEqual(tap2pcap.checksum(bytes.fromhex("0001f203f4f5f6f7")), 0x220D)
        self.assertEqual(tap2pcap.checksum(b"\x01"), 0xFEFF)

    def test_header(self):
        header, packets = convert(tap2pcap.Connection("10.0.0.1", 80, "10.0.0.2", 1234), [])
        self.assertEqual(
            header, dict(magic=0xA1B2C3D4, version=(2, 4), snaplen=262144, linktype=1))
        self.assertEqual(packets, [])

    def test_ipv4_stream(self):
        events = [
            (tap2pcap.READ, 100, 999999999, b"hello"),
            (tap2pcap.WRITE, 101, 1000, b"hi"),
            (tap2pcap.READ, 102, 0, b"!"),
        ]
        _, packets = convert(tap2pcap.Connection("10.0.0.1", 80, "10.0.0.2", 1234), events)
        self.assertEqual(
            [(p["seconds"], p["micros"]) for p in packets], [(100, 999999), (101, 1), (102, 0)])
        self.assertEqual(
            [(p["src"], p["sport"], p["dst"], p["dport"]) for p in packets],
            [("10.0.0.2", 1234, "10.0.0.1", 80), ("10.0.0.1", 80, "10.0.0.2", 1234),
             ("10.0.0.2", 1234, "10.0.0.1", 80)])
        self.assertEqual([p["payload"] for p in packets], [b"hello", b"hi", b"!"])
        # Each end's sequence numbers advance with what it sent, and acknowledge the other end's.
        self.assertEqual([(p["seq"], p["ack"]) for p in packets], [(1, 1), (1, 6), (6, 3)])
        self.assertEqual([p["ident"] for p in packets], [1, 2, 3])
        self.assertEqual({p["flags"] for p in packets}, {0x18})
        self.assertEqual(packets[0]["smac"], packets[1]["dmac"])
        self.assertEqual(packets[0]["dmac"], packets[1]["smac"])
        self.assertNotEqual(packets[0]["smac"], packets[0]["dmac"])

    def test_ipv6_stream(self):
        events = [(tap2pcap.WRITE, 1, 0, b"abc"), (tap2pcap.READ, 2, 0, b"de")]
        _, packets = convert(tap2pcap.Connection("::1", 443, "2001:db8::2", 5000), events)
        self.assertEqual(
            [(p["src"], p["sport"], p["dst"], p["dport"]) for p in packets],
            [("::1", 443, "2001:db8::2", 5000), ("2001:db8::2", 5000, "::1", 443)])
        self.assertEqual([p["payload"] for p in packets], [b"abc", b"de"])
        self.assertEqual([(p["seq"], p["ack"]) for p in packets], [(1, 1), (1, 4)])

    def test_segmentation(self):
        data = bytes(range(256)) * 600
        for connection in (tap2pcap.Connection("10.0.0.1", 80, "10.0.0.2", 1234),
                           tap2pcap.Connection("::1", 80, "::2", 1234)):
            _, packets = convert(connection, [(tap2pcap.READ, 1, 0, data)])
            self.assertEqual(len(packets), 3)
            self.assertEqual(b"".join(p["payload"] for p in packets), data)
            self.assertEqual(
                [p["seq"] for p in packets],
                [1, 1 + tap2pcap.MAX_SEGMENT, 1 + 2 * tap2pcap.MAX_SEGMENT])
            self.assertEqual({(p["seconds"], p["micros"]) for p in packets}, {(1, 0)})

    def test_empty_event(self):
        _, packets = convert(
            tap2pcap.Connection("10.0.0.1", 80, "10.0.0.2", 1234), [(tap2pcap.READ, 1, 0, b"")])
        self.assertEqual(packets, [])

    def test_bad_connection(self):
        with self.assertRaises(tap2pcap.TapError):
            tap2pcap.Connection("10.0.0.1", 80, "::1", 1234)
        with self.assertRaises(tap2pcap.TapError):
            tap2pcap.Connection("/var/run/envoy.sock", 0, "10.0.0.2", 1234)
        connection = tap2pcap.Connection("10.0.0.1", 80, "10.0.0.2", 1234)
        with self.assertRaises(tap2pcap.TapError):
            list(connection.frames("sideways", b"data"))


if __name__ == "__main__":
    unittest.main()
