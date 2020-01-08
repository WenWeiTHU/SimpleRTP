import socket, threading, random, os, time, cv2, sys
from RtpPacket import *
from RtcpPacket import *
from utils import *


BUFF_SIZE = 60000       # rtp socker receive size
RTCP_SR_PEROID = 500    # every RTCP_SR_PEROID frames send a sr rtcp packet

SUPPORTED_VIDEO_FORMAT = ['mp4', 'avi', 'flv', 'mkv', 'mov']

class ClientSession:
    """reocord every client's info and data"""
    def __init__(self, rtspSocket):
        self.sessionId = random.randint(1, 10000)
        self.ssrc = random.randint(1, 10000)
        self.rtspSocket = rtspSocket
        self.request = -1
        self.bytesSend = 0
        self.quality = '480P'
        self.speed = 1
    

class Server:
    def __init__(self, addr='127.0.0.1', rtspport='554', ftpport = '521', folder='video'):
        """initialization"""
        # addr: server ip address
        # rtsp port: listening stream video control connection
        # ftp port: listening file tranfering connection
        # folder: the folder where the videos store
        self.addr = addr
        self.rtspport = int(rtspport)
        self.ftpport = int(ftpport)      # for video downloading feature
        self.folder = folder        # set the video root folder
        self.getAllVideo()
        self.startListenRtsp()

    def getAllVideo(self):
        """return all video in root folder"""
        files = os.listdir(os.getcwd()+'/'+self.folder)
        self.videoList = []
        for file in files:
            if file.split('.')[-1] in SUPPORTED_VIDEO_FORMAT:
                self.videoList.append(file)
        self.videoList = '\n'.join(self.videoList)

    def startListenRtsp(self):
        """listen rtsp connection"""
        self.lisnRtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lisnRtspSocket.bind((self.addr, self.rtspport))
        self.lisnRtspSocket.listen()
        while True:
            connRtspSocket, addr = self.lisnRtspSocket.accept()
            connRtspSocket.send(self.videoList.encode())
            threading.Thread(target=self.recvRtspRequest, args=(connRtspSocket, addr)).start()

    def recvRtspRequest(self, connRtspSocket, addr):
        """thread of recv rstp"""
        print('Accept new rtsp connection from %s:%s...' % addr)
        clientSess = ClientSession(connRtspSocket)
        clientSess.frameNbr = 0
        clientSess.ip, clientSess.rtspPort = addr

        # once rtsp socket has established, start ftp tranfer socker listening
        self.lisnFtpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.lisnFtpSocket.bind((self.addr, self.ftpport))
        self.lisnFtpSocket.listen()
        clientSess.connFtpSocket, addr = self.lisnFtpSocket.accept()
        self.lisnFtpSocket.close()

        while True:
            data = clientSess.rtspSocket.recv(1024)
            if data:
                # print('Recv rtsp data: ', data)
                self.parseRtspRequest(data, clientSess)
            if (not data) or clientSess.requestType == 'TEARDOWN':
                break
        print('Connection from %s:%s closed.' % addr)

    def parseRtspRequest(self, data, clientSess):
        """parse rtsp reply from the client."""
        lines = str(data.decode()).split('\n')
        # print(lines)
        clientSess.requestType = lines[0].split(' ')[0]

        # extract video name to be played/download
        if clientSess.requestType == 'DOWNLOAD':
            clientSess.downldFile = lines[0].split(' ')[1]
        else:
            clientSess.filename = lines[0].split(' ')[1]
        clientSess.seqNum = lines[1].split(' ')[1]

        # for initialization
        if clientSess.requestType == 'SETUP':
            clientSess.rtpPort = int(lines[2].split(' ')[3])
            clientSess.rtcpPort = clientSess.rtpPort + 1
            clientSess.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            clientSess.rtcpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            clientSess.rtcpSocket.bind(('', random.randint(10000, 20000)))
            threading.Thread(target=self.listenRtcp, args=(clientSess, )).start()

        elif clientSess.requestType == 'PLAY':
            clientSess.playEvent = threading.Event()
            clientSess.playEvent.clear()
            threading.Thread(target=self.sendRtpPacket, args=(clientSess,)).start()

        elif clientSess.requestType == 'PAUSE':
            clientSess.playEvent.set()

        elif clientSess.requestType == 'SPEED':
            clientSess.speed = float(lines[3].split(' ')[1])

        elif clientSess.requestType == 'QUALITY':
            clientSess.quality = lines[3].split(' ')[1]

        elif clientSess.requestType == 'REPOS':
            if hasattr(clientSess, 'playEvent'):
                clientSess.playEvent.set()
            time.sleep(0.1)
            clientSess.frameNbr = int(lines[3].split(' ')[1])
            clientSess.playEvent = threading.Event()
            clientSess.playEvent.clear()
            threading.Thread(target=self.sendRtpPacket, args=(clientSess,)).start()

        elif clientSess.requestType == 'CHANGE':
            if hasattr(clientSess, 'playEvent'):
                clientSess.playEvent.set()
            clientSess.speed = 1
            clientSess.quality = '480P'
            clientSess.frameNbr = int(lines[3].split(' ')[1])
            time.sleep(0.1)                                         # avoid thread dead-lock
            if hasattr(clientSess, 'videoCapture'):
                clientSess.videoCapture.release()
            # try to open the file
            clientSess.videoCapture = cv2.VideoCapture(self.folder+'/'+clientSess.filename)
            if clientSess.videoCapture.isOpened():
                clientSess.frameTotal = clientSess.videoCapture.get(cv2.CAP_PROP_FRAME_COUNT)
                clientSess.fps = clientSess.videoCapture.get(cv2.CAP_PROP_FPS)

        elif clientSess.requestType == 'DOWNLOAD':
            pass

        elif clientSess.requestType == 'TEARDOWN':
            pass

        self.sendRtspResponse(clientSess)

    def sendRtspResponse(self, clientSess):
        """send rtsp reply with format response"""

        # code 200 means OK, 400 means file not found or permission deny
        response = 'RTSP/1.0 ' + '200 OK\n' + 'CSeq: ' + str(clientSess.seqNum) + \
                   '\nSession: ' + str(clientSess.sessionId)

        if clientSess.requestType == 'SETUP':
            pass
        elif clientSess.requestType == 'CHANGE':
            if not clientSess.videoCapture.isOpened():
                response = 'RTSP/1.0 ' + '400 FILE NOT FOUND\n' + 'CSeq: ' + str(clientSess.seqNum) + \
                            '\nSession: ' + str(clientSess.sessionId)
            else:
                response += '\nFrameNum: ' + str(clientSess.frameTotal)
                response += '\nFPS: ' + str(clientSess.fps)
        elif clientSess.requestType == 'PLAY':
            pass
        elif clientSess.requestType == 'PAUSE':
            pass
        elif clientSess.requestType == 'SPEED':
            pass
        elif clientSess.requestType == 'QUALITY':
            pass
        elif clientSess.requestType == 'REPOS':
            pass
        elif clientSess.requestType == 'DOWNLOAD':
            if not os.path.exists(self.folder+'/'+clientSess.downldFile):
                print('Error: file not found: ' + clientSess.downldFile)
                response = 'RTSP/1.0 ' + '400 FILE NOT FOUND\n' + 'CSeq: ' + str(clientSess.seqNum) + \
                           '\nSession: ' + str(clientSess.sessionId)
            else:
                response += '\nFileSize: ' + str(os.stat(self.folder+'/'+clientSess.downldFile).st_size)
                # print('start sending file')
                threading.Thread(target=self.sendFtpPacket, args=(clientSess,)).start()

        if clientSess.requestType == 'TEARDOWN':
            clientSess.rtspSocket.send(response.encode())
            clientSess.rtspSocket.shutdown(socket.SHUT_RDWR)
            clientSess.rtspSocket.close()
            clientSess.connFtpSocket.shutdown(socket.SHUT_RDWR)
            clientSess.connFtpSocket.close()
            return

        clientSess.rtspSocket.send(response.encode())

    def sendRtpPacket(self, clientSess):
        """send rtp packets."""
        clientSess.videoCapture.set(cv2.CAP_PROP_POS_FRAMES, clientSess.frameNbr)

        success, frame = clientSess.videoCapture.read()
        if not success:
            # print('frame read fail')
            return
        while success:
            if clientSess.playEvent.isSet():
                # pause request received
                # temporary stop sending rtp packet
                # rtp port will not be shut up
                # print('transfer pictures pause')
                break

            if clientSess.requestType == 'TEARDOWN':
                # close all opened udp socket for the client
                clientSess.rtpSocket.shutdown(socket.SHUT_RDWR)
                clientSess.rtpSocket.close()
                clientSess.rtcpSocket.shutdown(socket.SHUT_RDWR)
                clientSess.rtcpSocket.close()
                clientSess.videoCapture.release()
                # print('transfer pictures over')
                break

            # set video quality
            if clientSess.quality == '720P':
                data = frameEncode(cv2.resize(frame, (1280, 720)), 60)
            elif clientSess.quality == '480P':
                data = frameEncode(cv2.resize(frame, (848, 480)), 75)
            elif clientSess.quality == '360P':
                data = frameEncode(cv2.resize(frame, (640, 360)), 95)

            index = 0
            length = len(data)
            clientSess.bytesSend += length
            # this part for packet distribute
            # divide one frame into several pieces to transfer
            while index < length:
                rtpPacket = RtpPacket()

                # marker=1 means the end of a frame
                if index + BUFF_SIZE > length:
                    marker = 1
                else:
                    marker = 0
                rtpPacket.encode(version=2, padding=0, extension=0,
                                 cc=0, seqnum=clientSess.frameNbr,
                                 marker=marker, pt=26, ssrc=0,
                                 payload=data[index: index + BUFF_SIZE])
                clientSess.rtpSocket.sendto(rtpPacket.getPacket(), (clientSess.ip, int(clientSess.rtpPort)))
                index += BUFF_SIZE

            # send rtcp sr report periodly
            if clientSess.frameNbr % RTCP_SR_PEROID == 0:
                self.sendRtcpPacket(clientSess)

            clientSess.frameNbr += 1

            # fomula to calculate the sending interval for each frame
            # slightly less than standard waiting time
            cv2.waitKey(800 // int(clientSess.fps * clientSess.speed))
            success, frame = clientSess.videoCapture.read()
            if clientSess.frameNbr >= clientSess.frameTotal:
                # print('movie read over')
                return

    def sendFtpPacket(self, clientSess):
        """transfering the video that client want to download"""
        with open(self.folder+'/'+clientSess.downldFile, 'rb') as f:
            while True:
                buf_read = f.read(1024)
                send_n = clientSess.connFtpSocket.send(buf_read)
                if send_n == 0:
                    break
        # print('file send over')

    def sendRtcpPacket(self, clientSess):
        """send format rtcp sr packet to client"""
        rtcpPacket = RtcpSRPacket()
        rtcpPacket.encode(version=2, padding=0, rc=0,
                          ssrc=clientSess.ssrc, pcount=clientSess.frameNbr,
                          octcount=clientSess.bytesSend)
        clientSess.rtcpSocket.sendto(rtcpPacket.getPacket(), (clientSess.ip, int(clientSess.rtcpPort)))

    def listenRtcp(self, clientSess):
        """receive format rtcp rr report and show at console"""
        while True:
            rr = clientSess.rtcpSocket.recv(1024)
            if rr:
                rtcpPacket = RtcpRRPacket()
                rtcpPacket.decode(rr)
                print('----- Receiver Report -----')
                print('Version: ', rtcpPacket.version())
                print('PT: ', rtcpPacket.getPT())
                print('Reporter SSRC', rtcpPacket.getReporterSSRC())
                print('Reportee SSRC: ', rtcpPacket.getReporteeSSRC())
                print('Cumulative lost:' ,rtcpPacket.getCumLost())
                print('Sequence number: ', rtcpPacket.getSeqNum())
                print('Interval jitter: ', rtcpPacket.getInterval())
                print('LSR: ', rtcpPacket.getLSR())
                print('DLSR: ', rtcpPacket.getDLSR())


if __name__ == '__main__':
    server = Server(rtspport=sys.argv[1], ftpport=sys.argv[2], folder=sys.argv[3])
