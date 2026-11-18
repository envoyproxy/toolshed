"""Convert an Envoy socket tap trace to PCAP.

Envoy's tap transport socket records the bytes read from and written to a connection, with the
addresses of its two ends. This writes them as a PCAP file, for Wireshark and other tools of the
PCAP ecosystem. The packets are synthesized from the addresses, ports and timestamps of the trace:
one TCP segment (with dummy Ethernet and IP headers) per read or write. It is not a wire capture.

The trace is read with the caller's own proto message class (see `tap2pcap` in `//tap:defs.bzl`),
so this has no dependency on the Envoy API, or on anything other than Python.
"""

import ipaddress
import struct
import sys

# The classic PCAP format, with microsecond timestamps.
PCAP_MAGIC = 0xA1B2C3D4
PCAP_VERSION = (2, 4)
PCAP_SNAPLEN = 262144
LINKTYPE_ETHERNET = 1

ETHERTYPES = {4: 0x0800, 6: 0x86DD}
IPPROTO_TCP = 6
TCP_PSH_ACK = 0x18
TCP_WINDOW = 65535
TTL = 64

# Locally administered addresses, one for each end of the connection.
MAC_LOCAL = bytes.fromhex("020000000001")
MAC_REMOTE = bytes.fromhex("020000000002")

# The most data that fits in a segment: the IPv4 total length is 16 bit, and includes both headers.
MAX_SEGMENT = 65535 - 20 - 20

READ = "read"
WRITE = "write"


class TapError(Exception):
    pass


def checksum(data):
    """The internet checksum (RFC 1071) of `data`."""
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return ~total & 0xFFFF


def tcp_segment(src, dst, sport, dport, seq, ack, payload):
    """A TCP header and `payload`, checksummed for the `src` and `dst` addresses."""
    length = 20 + len(payload)
    if src.version == 4:
        pseudo = src.packed + dst.packed + struct.pack("!BBH", 0, IPPROTO_TCP, length)
    else:
        pseudo = src.packed + dst.packed + struct.pack("!IHBB", length, 0, 0, IPPROTO_TCP)
    header = struct.pack(
        "!HHIIBBHHH", sport, dport, seq, ack, 5 << 4, TCP_PSH_ACK, TCP_WINDOW, 0, 0)
    header = header[:16] + struct.pack("!H", checksum(pseudo + header + payload)) + header[18:]
    return header + payload


def ip_packet(src, dst, ident, segment):
    """`segment` in an IPv4 or IPv6 packet."""
    if src.version == 6:
        return struct.pack("!IHBB", 6 << 28, len(segment), IPPROTO_TCP, TTL) \
            + src.packed + dst.packed + segment
    header = struct.pack(
        "!BBHHHBBH", (4 << 4) | 5, 0, 20 + len(segment), ident & 0xFFFF, 0, TTL, IPPROTO_TCP, 0) \
        + src.packed + dst.packed
    return header[:10] + struct.pack("!H", checksum(header)) + header[12:] + segment


class Connection:
    """The two ends of a tapped connection, and the state of the stream between them."""

    def __init__(self, local_address, local_port, remote_address, remote_port):
        try:
            self.local = ipaddress.ip_address(local_address)
            self.remote = ipaddress.ip_address(remote_address)
        except ValueError as e:
            raise TapError("Not an IP connection: %s" % e)
        if self.local.version != self.remote.version:
            raise TapError(
                "Mixed address families: %s (local), %s (remote)" % (self.local, self.remote))
        self.local_port = local_port
        self.remote_port = remote_port
        # The next sequence number of each end.
        self.seq = {READ: 1, WRITE: 1}
        self.ident = 0

    def frames(self, direction, payload):
        """Ethernet frames carrying `payload`: read from the remote end, or written to it."""
        if direction == READ:
            src, sport, smac = self.remote, self.remote_port, MAC_REMOTE
            dst, dport, dmac = self.local, self.local_port, MAC_LOCAL
            other = WRITE
        elif direction == WRITE:
            src, sport, smac = self.local, self.local_port, MAC_LOCAL
            dst, dport, dmac = self.remote, self.remote_port, MAC_REMOTE
            other = READ
        else:
            raise TapError("Unknown direction: %s" % direction)
        ethernet = dmac + smac + struct.pack("!H", ETHERTYPES[src.version])
        for offset in range(0, len(payload), MAX_SEGMENT):
            data = payload[offset:offset + MAX_SEGMENT]
            segment = tcp_segment(
                src, dst, sport, dport, self.seq[direction], self.seq[other], data)
            self.seq[direction] = (self.seq[direction] + len(data)) & 0xFFFFFFFF
            self.ident += 1
            yield ethernet + ip_packet(src, dst, self.ident, segment)


def write_pcap(out, connection, events):
    """Write `events` to the `out` binary file as PCAP.

    `events` are `(direction, seconds, nanos, data)`: the direction is `READ` or `WRITE`, and the
    time is that of the event since the epoch. Returns the number of packets written.
    """
    out.write(
        struct.pack(
            "<IHHiIII", PCAP_MAGIC, PCAP_VERSION[0], PCAP_VERSION[1], 0, 0, PCAP_SNAPLEN,
            LINKTYPE_ETHERNET))
    count = 0
    for direction, seconds, nanos, data in events:
        for frame in connection.frames(direction, data):
            out.write(struct.pack("<IIII", seconds, nanos // 1000, len(frame), len(frame)))
            out.write(frame)
            count += 1
    return count


def body(data):
    """The bytes of a tap `Body`, which holds them as either bytes or a string."""
    return data.as_bytes or data.as_string.encode()


def trace_connection(trace):
    """The `Connection` of a socket buffered trace."""
    local = trace.connection.local_address.socket_address
    remote = trace.connection.remote_address.socket_address
    if not (local.address and remote.address):
        raise TapError("The trace has no connection addresses")
    return Connection(local.address, local.port_value, remote.address, remote.port_value)


def trace_events(trace):
    """The read and write events of a socket buffered trace, as `write_pcap` takes them."""
    for event in trace.events:
        if event.HasField("read"):
            direction, data = READ, event.read.data
        elif event.HasField("write"):
            direction, data = WRITE, event.write.data
        else:
            continue
        yield direction, event.timestamp.seconds, event.timestamp.nanos, body(data)


def read_trace(message, tap_path):
    """Parse the trace wrapper at `tap_path` (text proto if `.pb_text`, else binary)."""
    wrapper = message()
    if tap_path.endswith(".pb_text"):
        from google.protobuf import text_format
        with open(tap_path, "r") as f:
            text_format.Merge(f.read(), wrapper)
    else:
        with open(tap_path, "rb") as f:
            wrapper.ParseFromString(f.read())
    return wrapper


def tap2pcap(message, tap_path, pcap_path):
    """Convert the trace at `tap_path` (a `message` trace wrapper) to PCAP at `pcap_path`."""
    wrapper = read_trace(message, tap_path)
    if not wrapper.HasField("socket_buffered_trace"):
        raise TapError("%s is not a socket buffered trace" % tap_path)
    trace = wrapper.socket_buffered_trace
    connection = trace_connection(trace)
    with open(pcap_path, "wb") as f:
        return write_pcap(f, connection, trace_events(trace))


def main(message, argv=None):
    argv = sys.argv if argv is None else argv
    if len(argv) != 3:
        print("Usage: %s <tap .pb/.pb_text> <pcap path>" % argv[0], file=sys.stderr)
        return 1
    try:
        tap2pcap(message, argv[1], argv[2])
    except TapError as e:
        print("ERROR: %s" % e, file=sys.stderr)
        return 1
    return 0
