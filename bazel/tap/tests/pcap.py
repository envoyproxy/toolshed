"""A reader for the PCAP files that `tap2pcap` writes, for its tests."""

import ipaddress
import struct


def ones_complement_sum(data):
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return total


def read_pcap(data):
    """The `(header, packets)` of a PCAP file, each packet a dict of its decoded fields.

    Checks the lengths and checksums of every layer on the way.
    """
    magic, major, minor, zone, sigfigs, snaplen, linktype = struct.unpack("<IHHiIII", data[:24])
    header = dict(magic=magic, version=(major, minor), snaplen=snaplen, linktype=linktype)
    packets = []
    offset = 24
    while offset < len(data):
        seconds, micros, caplen, length = struct.unpack("<IIII", data[offset:offset + 16])
        assert caplen == length
        frame = data[offset + 16:offset + 16 + caplen]
        assert len(frame) == caplen
        offset += 16 + caplen
        packets.append(dict(seconds=seconds, micros=micros, **read_frame(frame)))
    return header, packets


def read_frame(frame):
    dmac, smac, ethertype = frame[:6], frame[6:12], struct.unpack("!H", frame[12:14])[0]
    packet = frame[14:]
    if ethertype == 0x0800:
        assert packet[0] == 0x45
        total, ident = struct.unpack("!HH", packet[2:6])
        assert total == len(packet)
        assert packet[9] == 6
        assert ones_complement_sum(packet[:20]) == 0xFFFF
        src, dst = packet[12:16], packet[16:20]
        segment = packet[20:]
        pseudo = src + dst + struct.pack("!BBH", 0, 6, len(segment))
    elif ethertype == 0x86DD:
        assert packet[0] >> 4 == 6
        length = struct.unpack("!H", packet[4:6])[0]
        assert packet[6] == 6
        src, dst = packet[8:24], packet[24:40]
        segment = packet[40:]
        assert length == len(segment)
        ident = None
        pseudo = src + dst + struct.pack("!IHBB", len(segment), 0, 0, 6)
    else:
        raise AssertionError("Unexpected ethertype: %x" % ethertype)
    sport, dport, seq, ack, offset, flags, window = struct.unpack("!HHIIBBH", segment[:16])
    assert offset == 5 << 4
    assert ones_complement_sum(pseudo + segment) == 0xFFFF
    return dict(
        dmac=dmac,
        smac=smac,
        ident=ident,
        src=str(ipaddress.ip_address(src)),
        dst=str(ipaddress.ip_address(dst)),
        sport=sport,
        dport=dport,
        seq=seq,
        ack=ack,
        flags=flags,
        window=window,
        payload=segment[20:])
