import sys, time

RTCP_SR_HEADER_SIZE = 28
RTCP_RR_HEADER_SIZE = 32
RTCP_SDES_HEADER_SIZE = 4
RTCP_BYE_HEADER_SIZE = 8

"""
    Define RTCP packet format
    Reference : https://tools.ietf.org/html/rfc3550#section-6.4
"""

class RtcpSRPacket:
    """
        RTCP sender report packet format
        Reference : https://tools.ietf.org/html/rfc3550#section-6.4.1
    """

    header = bytearray(RTCP_SR_HEADER_SIZE)

    def __init__(self):
        pass

    def encode(self, version, padding, rc, ssrc, pcount, octcount):
        """Encode the RTP packet with header fields and payload."""
        timestamp = int(time.time())
        ntptime = int(time.time())
        ntptime_high = int(ntptime)
        ntptime_low = ntptime - ntptime_high
        pt = 200
        length = 28
        header = bytearray(RTCP_SR_HEADER_SIZE)

        # Fill the header bytearray with RTP header fields
        header[0] = (version << 6) | (padding << 5) | rc
        header[1] = pt
        header[2] = (length >> 8) & 255  # upper bits
        header[3] = length & 255

        header[4] = ssrc >> 24 & 255
        header[5] = ssrc >> 16 & 255
        header[6] = ssrc >> 8 & 255
        header[7] = ssrc & 255

        header[8] = ntptime_high >> 24 & 255
        header[9] = ntptime_high >> 16 & 255
        header[10] = ntptime_high >> 8 & 255
        header[11] = ntptime_high & 255

        header[12] = ntptime_low >> 24 & 255
        header[13] = ntptime_low >> 16 & 255
        header[14] = ntptime_low >> 8 & 255
        header[15] = ntptime_low & 255

        header[16] = timestamp >> 24 & 255
        header[17] = timestamp >> 16 & 255
        header[18] = timestamp >> 8 & 255
        header[19] = timestamp & 255

        header[20] = pcount >> 24 & 255
        header[21] = pcount >> 16 & 255
        header[22] = pcount >> 8 & 255
        header[23] = pcount & 255

        header[24] = octcount >> 24 & 255
        header[25] = octcount >> 16 & 255
        header[26] = octcount >> 8 & 255
        header[27] = octcount & 255
        self.header = header

    def decode(self, byteStream):
        """Decode the RTP packet."""
        self.header = bytearray(byteStream[:RTCP_SR_HEADER_SIZE])

    def version(self):
        """Return RTP version."""
        return int(self.header[0] >> 6)
    
    def timestamp(self):
        """Return timestamp."""
        timestamp = self.header[16] << 24 | self.header[17] << 16 | self.header[18] << 8 | self.header[19]
        return int(timestamp)
    
    def ntptime(self):
        """Return ntptimestamp."""
        ntptime_high = self.header[8] << 24 | self.header[9] << 16 | self.header[10] << 8 | self.header[11]
        ntptime_low = self.header[12] << 24 | self.header[13] << 16 | self.header[14] << 8 | self.header[15]
        return int(ntptime_high) + float(ntptime_low)

    def getPT(self):
        return 200

    def getSSRC(self):
        ssrc = self.header[4] << 24 | self.header[5] << 16 | self.header[6] << 8 | self.header[7]
        return int(ssrc)

    def getPacketCount(self):
        pcount = self.header[20] << 24 | self.header[21] << 16 | self.header[22] << 8 | self.header[23]
        return int(pcount)

    def getOctetCount(self):
        octcount = self.header[24] << 24 | self.header[25] << 16 | self.header[26] << 8 | self.header[27]
        return int(octcount)

    def getPacket(self):
        return self.header


class RtcpRRPacket:
    """
        RTCP receiver report packet format
        Reference : https://tools.ietf.org/html/rfc3550#section-6.4.1
    """

    header = bytearray(RTCP_RR_HEADER_SIZE)

    def __init__(self):
        pass

    def encode(self, version, padding, rc, ssrc, recvssrc,\
              lost, seq, interval, lsr, dlsr):
        """Encode the RTP packet with header fields and payload."""
        timestamp = int(time.time())
        ntptime = int(time.time())
        ntptime_high = int(ntptime)
        ntptime_low = ntptime - ntptime_high
        pt = 201
        length = 28
        header = bytearray(RTCP_RR_HEADER_SIZE)

        # Fill the header bytearray with RTP header fields
        header[0] = (version << 6) | (padding << 5) | rc
        header[1] = pt
        header[2] = (length >> 8) & 255  # upper bits
        header[3] = length & 255

        header[4] = ssrc >> 24 & 255
        header[5] = ssrc >> 16 & 255
        header[6] = ssrc >> 8 & 255
        header[7] = ssrc & 255

        header[8] = recvssrc >> 24 & 255
        header[9] = recvssrc >> 16 & 255
        header[10] = recvssrc >> 8 & 255
        header[11] = recvssrc & 255

        header[12] = 0
        header[13] = lost >> 16 & 255
        header[14] = lost >> 8 & 255
        header[15] = lost & 255

        header[16] = seq >> 24 & 255
        header[17] = seq >> 16 & 255
        header[18] = seq >> 8 & 255
        header[19] = seq & 255

        header[20] = interval >> 24 & 255
        header[21] = interval >> 16 & 255
        header[22] = interval >> 8 & 255
        header[23] = interval & 255

        header[24] = lsr >> 24 & 255
        header[25] = lsr >> 16 & 255
        header[26] = lsr >> 8 & 255
        header[27] = lsr & 255

        header[28] = dlsr >> 24 & 255
        header[29] = dlsr >> 16 & 255
        header[30] = dlsr >> 8 & 255
        header[31] = dlsr & 255

        self.header = header

    def decode(self, byteStream):
        """Decode the RTP packet."""
        self.header = bytearray(byteStream[:RTCP_RR_HEADER_SIZE])

    def version(self):
        """Return RTP version."""
        return int(self.header[0] >> 6)

    def getCumLost(self):
        lost = self.header[13] << 16 | self.header[14] << 8 | self.header[15]
        return 256 * int(lost)

    def getPT(self):
        return 201

    def getReporterSSRC(self):
        ssrc = self.header[4] << 24 | self.header[5] << 16 | self.header[6] << 8 | self.header[7]
        return int(ssrc)

    def getReporteeSSRC(self):
        ssrc = self.header[8] << 24 | self.header[9] << 16 | self.header[10] << 8 | self.header[11]
        return int(ssrc)

    def getSeqNum(self):
        seqnum = self.header[16] << 24 | self.header[17] << 16 | self.header[18] << 8 | self.header[19]
        return int(seqnum)

    def getInterval(self):
        interval = self.header[20] << 24 | self.header[21] << 16 | self.header[22] << 8 | self.header[23]
        return int(interval)

    def getLSR(self):
        lsr = self.header[24] << 24 | self.header[25] << 16 | self.header[26] << 8 | self.header[27]
        return int(lsr)

    def getDLSR(self):
        lsr = self.header[28] << 24 | self.header[29] << 16 | self.header[30] << 8 | self.header[31]
        return int(lsr)

    def getPacket(self):
        return self.header


class RtcpSDESPacket:
    """
        RTCP receiver SDES packet format
        Reference : https://tools.ietf.org/html/rfc3550#section-6.5
    """

    header = bytearray(RTCP_SDES_HEADER_SIZE)

    def __init__(self):
        pass

    def encode(self, version, padding, length, sc, ssrc, sdesitems):
        """Encode the RTP packet with header fields and payload."""
        pt = 202
        length = 4
        header = bytearray(RTCP_SDES_HEADER_SIZE)
        self.sdesitems = b''

        # Fill the header bytearray with RTP header fields
        header[0] = (version << 6) | (padding << 5) | sc
        header[1] = pt
        header[2] = (length >> 8) & 255  # upper bits
        header[3] = length & 255

        self.header = header

        for item in sdesitems:
            self.sdesitems += bytearray(item.ssrc)
            self.sdesitems += bytearray(item.sdesplayload)

    def getHeader(self):
        return self.header

    def getSDES(self):
        return self.sdeitems

    def version(self):
        """Return RTP version."""
        return int(self.header[0] >> 6)

    def getPT(self):
        return 202


class RtcpBYEPacket:
    header = bytearray(RTCP_BYE_HEADER_SIZE)

    """
        RTCP receiver YBE packet format
        Reference : https://tools.ietf.org/html/rfc3550#section-6.6
    """

    def __init__(self):
        pass

    def encode(self, version, padding, sc, ssrc):
        """Encode the RTP packet with header fields and payload."""
        pt = 203
        length = 8
        header = bytearray(RTCP_BYTE_HEADER_SIZE)

        # Fill the header bytearray with RTP header fields
        header[0] = (version << 6) | (padding << 5) | sc
        header[1] = pt
        header[2] = (length >> 8) & 255  # upper bits
        header[3] = length & 255

        header[4] = ssrc >> 24 & 255
        header[5] = ssrc >> 16 & 255
        header[6] = ssrc >> 8 & 255
        header[7] = ssrc & 255

    def version(self):
        """Return RTP version."""
        return int(self.header[0] >> 6)

    def getPT(self):
        return 203

    def getSSRC(self):
        ssrc = self.header[4] << 24 | self.header[5] << 16 | self.header[6] << 8 | self.header[7]
        return int(ssrc)

    def getPacket(self):
        return self.header