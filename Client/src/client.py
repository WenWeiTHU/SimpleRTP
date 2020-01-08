from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from RtpPacket import *
from RtcpPacket import *
from widgets import *
from utils import *
import cv2, numpy, time, threading
import socket, sys, traceback, os, random
# import pygame


MAX_PACK_SIZE = 40960
CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"


class Client(QMainWindow):
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    # supported command
    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    SPEED = 4
    REPOS = 5
    CHANGE = 6
    DOWNLOAD = 7
    QUALITY = 8

    # AUDIOREADY = 0
    # AUDIOPAUSED = 1

    def __init__(self, serveraddr='127.0.0.1', rtspport='554', ftpport='521', rtpport='10000'):
        """initialization"""  
        # serveraddr: server ip to be connected      (decided by server)
        # rtspport: server rtsp port to be connected (decided by server)
        # ftpport:  server ftp port to be connected  (decided by server)
        # rtpport: client rtp port                   (decided by client)
        super().__init__()

        self.fileName = ''
        self.ssrc = random.randint(1, 10000)
        self.serverAddr = serveraddr
        self.serverPort = int(rtspport)         # server rtsp port
        self.rtpPort = int(rtpport)             # rtp port is even port
        self.rtcpPort = self.rtpPort + 1        # rtcp port = rtp port + 1
        self.ftpPort = int(ftpport)             # server ftp port
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.frameNbr = 0
        self.lost = 0
        self.speed = 1
        self.quality = '480P'
        self.initUI()
        self.initSlot()
        self.connectToServer()
        time.sleep(0.2)
        self.setupMovie()
        self.screenShotIndex = 0

        self.historyRec = {}                    # for history play record
        # pygame.mixer.init()

    def initUI(self):
        """init Qt UI"""
        self.grid = QGridLayout()
        self.mainWidget = QTabWidget()
        self.playWidget = QWidget()
        self.videoAllWidget = QWidget()

        self.mainWidget.addTab(self.videoAllWidget, 'Videos')
        self.listWidget = RemoteFileWidget()
        self.downldLabel = QLabel('')
        self.downldLabel.setFixedHeight(12)
        self.searchEdit = QLineEdit()
        self.searchEdit.setPlaceholderText('Search Video')
        self.searchEdit.setClearButtonEnabled(True)

        self.videoGrid = QGridLayout()
        self.videoAllWidget.setLayout(self.videoGrid)
        self.videoGrid.addWidget(self.searchEdit, 0, 0, 1, 4)
        self.videoGrid.addWidget(self.listWidget, 1, 0, 3, 4)
        self.videoGrid.addWidget(self.downldLabel, 5, 0, 1, 1)

        self.mainWidget.addTab(self.playWidget, 'Player')
        self.playWidget.setLayout(self.grid)
        self.titleLabel = QLabel()
        self.imgLabel = QMovieLabel()
        self.playBtn = QPushButton('Play')
        self.reconnBtn = QPushButton('Reconnect')
        self.playSlider = QSlider(Qt.Horizontal)
        self.fuScrBtn = QPushButton('Full Screen')
        self.speedComb = QComboBox()
        self.qualityComb = QComboBox()

        self.srtBtn = QPushButton('Subtitle file')
        self.srtLabel = QLabel()


        self.timeLabel = QLabel('00:00:00/00:00:00')

        self.autoCKBox = QCheckBox('Auto Replay')
        self.autoCKBox.setChecked(False)

        self.downldBtn = QPushButton('Download')
        self.scrShotBtn = QPushButton('ScreenShot')

        self.speedComb.addItems(['0.25', '0.5', '0.75', '1.0', '1.25', '1.5', '1.75', '2.0'])
        self.speedComb.setCurrentIndex(3)

        self.qualityComb.addItems(['360P', '480P', '720P'])
        self.qualityComb.setCurrentIndex(1)

        self.timeLabel.setFixedHeight(10)

        self.titleLabel.setFixedHeight(12)
        self.imgLabel.setScaledContents(True)
        self.setCentralWidget(self.mainWidget)


        self.grid.addWidget(self.titleLabel, 0, 0, 1, 4)
        self.grid.addWidget(self.imgLabel, 1, 0, 3, 4)


        self.grid.addWidget(self.srtLabel, 4, 0, 1, 4)

        self.grid.addWidget(self.playSlider, 5, 1, 1, 3)
        self.grid.addWidget(self.timeLabel, 5, 0, 1, 1)
        self.grid.addWidget(self.playBtn, 6, 0, 1, 1)
        self.grid.addWidget(self.autoCKBox, 6, 1, 1, 1)
        self.grid.addWidget(self.srtBtn, 6, 3, 1, 1)
        self.grid.addWidget(self.speedComb, 6, 2, 1, 1)
        self.grid.addWidget(self.downldBtn, 7, 0, 1, 1)
        self.grid.addWidget(self.reconnBtn, 7, 1, 1, 1)
        self.grid.addWidget(self.qualityComb, 7, 2, 1, 1)
        self.grid.addWidget(self.scrShotBtn, 7, 3, 1, 1)

        self.setFixedSize(800, 600)
        self.setWindowTitle('RSTCP Player')
        self.show()

    def initSlot(self):
        """init slot connections"""
        self.playBtn.clicked.connect(self.playPause)
        self.reconnBtn.clicked.connect(self.reconnect)
        self.speedComb.currentIndexChanged.connect(self.changeSpeed)
        self.qualityComb.currentIndexChanged.connect(self.changeQuality)
        self.playSlider.sliderPressed.connect(self.pauseMovie)
        self.playSlider.sliderReleased.connect(self.reposition)
        # self.playSlider.rePosSig.changePos.connect(self.reposition)
        # self.fuScrBtn.clicked.connect(self.showFull)
        self.listWidget.fileSignals.filename.connect(self.changeMovie)
        self.listWidget.downldSignals.filename.connect(self.downldFile)
        self.downldBtn.clicked.connect(lambda: self.downldFile(self.fileName))
        self.imgLabel.playPauseSig.playPause.connect(self.playPause)
        self.searchEdit.textChanged.connect(self.updateVideoList)
        self.scrShotBtn.clicked.connect(self.screenShot)
        self.srtBtn.clicked.connect(self.readSrtFile)

    def readSrtFile(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "select subtitle file","", "srt files (*.srt)")
        try:
            self.srtDic = readSrt(fileName)
        except Exception as e:
            print(e)
            print('subtitle file open failed')
        else:
            self.statusBar().showMessage('Open subtitle file ' +  fileName.split('/')[-1] + ' successfully')
            self.changeMovieEvent = threading.Event()
            self.changeMovieEvent.clear()
            threading.Thread(target=self.showSubtitle).start()

    def showSubtitle(self):
        timeS = self.srtDic.keys()
        while True:
            timeMark = formatPlayTime(self.frameNbr, self.frameTotal, self.fps).split('/')[0]
            if timeMark in timeS:
                self.srtLabel.setText(self.srtDic[timeMark])
            time.sleep(1)
            if self.teardownAcked == 1:
                break
            if self.changeMovieEvent.is_set():
                break

    def screenShot(self):
        """store screenshot"""
        screenShot = self.imgLabel.pixmap()
        shotName = '_'.join(['SCREENSHOT', str(self.sessionId),\
                             str(self.screenShotIndex)]) + '.png'
        screenShot.save(shotName)
        self.screenShotIndex += 1

    def downldFile(self, filename):
        """download remote file"""
        if not filename:
            QMessageBox.information(self, 'No file', 'No movie specified',
                                    QMessageBox.Close, QMessageBox.Close)
            return
        self.downldfile = filename
        # self.downldLabel.setText('Downloading ' + filename + '...')
        self.statusBar().showMessage('Downloading ' + filename + '...')
        self.downldBtn.setDisabled(True)
        self.sendRtspRequest(self.DOWNLOAD)

    # def showFull(self):
    #     """show full screen"""
    #     self.showFullScr = True
    #     self.playSlider.hide()
    #     self.playBtn.hide()
    #     self.reconnBtn.hide()
    #     self.fuScrBtn.hide()
    #     self.srtBtn.hide()
    #     self.srtLabel.hide()
    #     self.speedComb.hide()
    #     self.qualityComb.hide()
    #     self.autoCKBox.hide()
    #     self.timeLabel.hide()
    #     self.scrShotBtn.hide()
    #     self.titleLabel.hide()
    #     self.downldBtn.hide()
    #     self.statusBar().hide()
    #     self.showFullScreen()
    #
    #     self.fuScrBtn.setEnabled(False)
    #     threading.Timer(5.0, self.test).start()
    #
    # def test(self):
    #     self.fuScrBtn.setEnabled(True)
    #
    #
    # def showNorm(self):
    #     """press ESC to recover from full screen"""
    #     self.showFullScr = False
    #     self.playSlider.show()
    #     self.playBtn.show()
    #     self.reconnBtn.show()
    #     self.srtBtn.show()
    #     self.srtLabel.show()
    #     self.fuScrBtn.show()
    #     self.speedComb.show()
    #     self.timeLabel.show()
    #     self.qualityComb.show()
    #     self.autoCKBox.show()
    #     self.scrShotBtn.show()
    #     self.titleLabel.show()
    #     self.downldBtn.show()
    #     self.statusBar().show()
    #     self.showNormal()

    def playPause(self):
        """click the screen for play/pause"""
        if self.state == self.PLAYING:
            self.playBtn.setText('Play')
            self.pauseMovie()
        elif self.state == self.READY:
            self.playBtn.setText('Pause')
            self.playMovie()

    def reposition(self):
        """drag slider for reposition"""
        if self.frameTotal - self.playSlider.value() < 10:
            self.playSlider.setValue(self.playSlider.value() - 10)
        self.frameNbr = self.playSlider.value()
        if hasattr(self, 'playEvent'):
            self.playEvent.set()
        self.srtLabel.setText('')
        self.sendRtspRequest(self.REPOS)
        self.playBtn.setText('Pause')
        self.statusBar().showMessage('Playing')
        time.sleep(0.1)
        threading.Thread(target=self.listenRtp).start()
        self.playEvent = threading.Event()
        self.playEvent.clear()

    def setupMovie(self):
        """setup connection needed and some initialization"""
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def updateVideoList(self):
        """show videos in Qt UI"""
        self.listWidget.clear()
        for file in self.videoList:
            if self.searchEdit.text() in file:
                fItem = QListWidgetItem(file)
                fItem.setIcon(QIcon('assets/video.png'))
                fItem.setTextAlignment(Qt.AlignCenter)
                self.listWidget.addItem(fItem)

    def changeMovie(self, filename):
        """select other movie to play"""
        if self.fileName:
            self.historyRec[self.fileName] = self.frameNbr
        # print(self.historyRec)

        self.fileName = filename

        # reposition to historical played position
        if filename in self.historyRec.keys():
            self.frameNbr = self.historyRec[filename]
            self.statusBar().showMessage('Set to last playback position')
        else:
            self.frameNbr = 0
            self.statusBar().showMessage('Ready')
        self.playSlider.setValue(self.frameNbr)

        self.speed = 1
        self.quality = '480P'
        self.speedComb.setCurrentIndex(3)
        self.qualityComb.setCurrentIndex(1)
        self.mainWidget.setCurrentIndex(1)
        self.sendRtspRequest(self.CHANGE)

        if hasattr(self, 'changeMovieEvent'):
            self.changeMovieEvent.set()
            self.srtLabel.setText('')

        self.titleLabel.setText(filename)

        # self.audioName = ''.join(self.fileName.split('.')[:-1]) + '.mp3'
        # if os.path.exists(filename):
        #     print('file already exists')
        #     return
        # self.downldFile(self.audioName)
        # self.playBtn.setText('Waiting...')
        # self.playBtn.setEnabled(False)

    def exitClient(self):
        """teardown button handler"""
        print('sucessfully exit')
        self.sendRtspRequest(self.TEARDOWN)

    def pauseMovie(self):
        """pause button handler"""
        if self.state == self.PLAYING:
            self.statusBar().showMessage('Paused')
            self.sendRtspRequest(self.PAUSE)

    def playMovie(self):
        """play button handler"""
        if not self.fileName:
            QMessageBox.information(self, 'No file', 'No movie specified',
                                    QMessageBox.Close, QMessageBox.Close)
            return
        if self.state == self.READY:
            # Create a new thread to listen for RTP packets
            self.statusBar().showMessage('Playing')
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)

    def changeSpeed(self):
        """change play speed"""
        self.speed = float(self.speedComb.currentText())
        self.sendRtspRequest(self.SPEED)

    def changeQuality(self):
        """change video quality"""
        self.quality = self.qualityComb.currentText()
        self.sendRtspRequest(self.QUALITY)

    def listenRtcp(self):
        """receiving sr rtcp report"""
        while True:
            try:
                sr, self.rtcpaddr = self.rtcpSocket.recvfrom(1024)
            except Exception:
                # print("Remote server has closed the connection")
                break
            if sr:
                print('----- Sender Report -----')
                rtcpPacket = RtcpSRPacket()
                rtcpPacket.decode(sr)
                print('Version: ', rtcpPacket.version())
                print('PT:' ,rtcpPacket.getPT())
                print('SSRC: ', rtcpPacket.getSSRC())
                print('Timestamp: ', rtcpPacket.timestamp())
                print('NTP timestamp: ', rtcpPacket.ntptime())
                print('Packet count: ', rtcpPacket.getPacketCount())
                print('Octet count: ', rtcpPacket.getOctetCount())

            # reply rtcp rr report to server
            replyPacket = RtcpRRPacket()
            replyPacket.encode(version=2, padding=0, rc=0,
                               ssrc=rtcpPacket.getSSRC(),
                               recvssrc=self.ssrc,
                               lost=self.lost,
                               seq=self.frameNbr,
                               interval=1,
                               lsr=rtcpPacket.timestamp(),
                               dlsr=int(time.time()-rtcpPacket.timestamp()))
            self.rtcpSocket.sendto(replyPacket.getPacket(), self.rtcpaddr)

    def listenRtp(self):
        """Listen for RTP packets."""
        # print('start rtp listening')
        # if self.audioState == self.AUDIOREADY:
        #     pygame.mixer.music.play()
        # elif self.audioState == self.AUDIOPAUSED:
        #     pygame.mixer.music.unpause()
        currFrameNbr = 0
        frameBuff = b''
        while True:
            try:
                data = self.rtpSocket.recv(61440)
                if data:
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)
                    currFrameNbr = rtpPacket.seqNum()

                    # compose frame pieces into a frame
                    if self.frameNbr == currFrameNbr:
                        frameBuff += rtpPacket.getPayload()
                        if rtpPacket.getMarker() == 1:
                            self.updateMovie(frameBuff)
                            frameBuff = b''
                            self.frameNbr += 1
                            self.playSlider.setValue(self.frameNbr)
                            self.timeLabel.setText(formatPlayTime(self.frameNbr, self.frameTotal, self.fps))



                    # if new frame comes while the old frame is to completely composed
                    # just discard the late packet
                    elif currFrameNbr > self.frameNbr:
                        if rtpPacket.getMarker() == 0:
                            frameBuff = b''
                            frameBuff += rtpPacket.getPayload()
                            self.frameNbr = currFrameNbr

            except Exception as e:
                # print(e) # this means time out, waiting for other user input

                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet():
                    # pygame.mixer.music.pause()
                    # self.audioState = self.AUDIOPAUSED
                    break

                # video play over
                elif self.frameTotal - currFrameNbr <= 10:
                    self.playSlider.setValue(0)
                    
                    self.reposition()

                    if self.autoCKBox.isChecked():
                        # if auto-replay button set, go back to play
                        self.playMovie()
                    else:
                        # otherwise, waiting user input
                        self.playBtn.setText('Play')
                        self.pauseMovie()
                        self.imgLabel.setPixmap(QPixmap('assets/replay.png'))

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()
                break

    def updateMovie(self, buf):
        """update the image file as video frame in the UI"""
        photo = QPixmap()
        ok = photo.loadFromData(buf, 'JPG')
        if ok:
            self.imgLabel.setPixmap(photo)
        else:
            self.lost += 1

    def connectToServer(self):
        """Connect to the Server. Start a new RTSP/TCP session"""
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            QMessageBox.information(self, 'Connection Failed', 'Rtsp: Connection to \'%s\' failed.' % self.serverAddr,
                                    QMessageBox.Close, QMessageBox.Close)
        else:
            # if rtsp connection established successfully, try to connect ftp socket
            reply = self.rtspSocket.recv(1024)
            self.videoList = reply.decode().split('\n')
            self.updateVideoList()

            self.ftpSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                self.ftpSocket.connect((self.serverAddr, self.ftpPort))
                self.statusBar().showMessage('Ready')
            except:
                QMessageBox.information(self, 'Connection Failed', 'Ftp: Connection to \'%s\' failed.' % self.serverAddr,
                                        QMessageBox.Close, QMessageBox.Close)

    def sendRtspRequest(self, requestCode):
        """send RTSP request to the server"""

        # Setup request
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number.
            self.rtspSeq += 1
            # Write the RTSP request to be sent.
            request = 'SETUP ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq)\
                      + '\nTransport: RTP/UDP; client_port= ' + str(self.rtpPort)

            # Keep track of the sent request.
            self.requestSent = self.SETUP

        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            # movie has chosen for play
            self.rtspSeq += 1
            request = 'PLAY ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq)\
                      + '\nSession: ' + str(self.sessionId)
            self.requestSent = self.PLAY

        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            self.rtspSeq += 1
            request = 'PAUSE ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq)\
                      + '\nSession: ' + str(self.sessionId)
            self.requestSent = self.PAUSE

        # Teardown request
        elif requestCode == self.TEARDOWN:
            self.rtspSeq += 1
            request = 'TEARDOWN ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionId)
            # print('send teardown')

            self.requestSent = self.TEARDOWN

        # Change play speed request
        elif requestCode == self.SPEED and not self.state == self.INIT:
            self.rtspSeq += 1
            request = 'SPEED ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionId) + '\nSpeed: ' + str(self.speed)
            self.requestSent = self.SPEED

        # Change video quality request
        elif requestCode == self.QUALITY and not self.state == self.INIT:
            self.rtspSeq += 1
            request = 'QUALITY ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionId) + '\nSpeed: ' + str(self.quality)
            self.requestSent = self.QUALITY

        # Reposition request
        elif requestCode == self.REPOS and not self.state == self.INIT:
            self.rtspSeq += 1
            request = 'REPOS ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionId) + '\nRange: ' + str(self.frameNbr)
            self.requestSent = self.REPOS

        # Change to play other movie
        elif requestCode == self.CHANGE and not self.state == self.INIT:
            self.rtspSeq += 1
            request = 'CHANGE ' + self.fileName + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionId) + '\nRange: ' + str(self.frameNbr)
            # Keep track of the sent request.
            self.requestSent = self.CHANGE

        # Download movie request
        elif requestCode == self.DOWNLOAD and not self.state == self.INIT:
            self.rtspSeq += 1
            # Write the FTP request to be sent.
            request = 'DOWNLOAD ' + self.downldfile + ' RTSP/1.0\nCSeq: ' + str(self.rtspSeq) + '\nSession: ' + str(
                self.sessionId)
            # Keep track of the sent request.
            threading.Thread(target=self.storeFile).start()
            self.requestSent = self.DOWNLOAD
        else:
            return

        # Send the RTSP request using rtspSocket.
        self.rtspSocket.send(request.encode())

        # print('\nData sent:\n' + request)

    def reconnect(self):
        self.rtspSocket.shutdown(socket.SHUT_RDWR)
        self.rtspSocket.close()
        self.ftpSocket.shutdown(socket.SHUT_RDWR)
        self.ftpSocket.close()
        self.rtpSocket.shutdown(socket.SHUT_RDWR)
        self.rtpSocket.close()
        self.rtcpSocket.shutdown(socket.SHUT_RDWR)
        self.rtcpSocket.close()
        self.lost = 0
        self.playBtn.setText("Play")
        self.state = self.INIT
        self.ssrc = random.randint(1, 10000)
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.lost = 0
        self.connectToServer()
        time.sleep(0.2)
        self.setupMovie()
        time.sleep(1)
        self.changeMovie(self.fileName)

    def recvRtspReply(self):
        """receive RTSP reply from the server"""
        while True:
            try:
                reply = self.rtspSocket.recv(1024)
            except Exception:
                self.statusBar().showMessage('Remote server has shut down the connection, please try to reconnect')
                break

            if reply:
                self.parseRtspReply(reply.decode("utf-8"))

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                self.rtcpSocket.shutdown(socket.SHUT_RDWR)
                self.rtcpSocket.close()
                self.ftpSocket.shutdown(socket.SHUT_RDWR)
                self.ftpSocket.close()
                break

    def storeFile(self):
        """store the downloaded file sent by server"""
        # total_write = 0
        try:
            with open(self.downldfile, 'wb') as f:
                while True:
                    buf_read = self.ftpSocket.recv(1024)
                    f.write(buf_read)
                    # total_write += len(buf_read)
                    if len(buf_read) < 1024:
                        # ('file recv over')
                        self.statusBar().showMessage('Download ' + self.downldfile + ' OK')
                        self.downldBtn.setDisabled(False)
                        self.downldLabel.setText('')
                        break
        except Exception:
            QMessageBox.information(self, 'Open failed',
                                    'Permission denied not file already exists',
                                    QMessageBox.Close, QMessageBox.Close)
        # finally:
        #     self.playBtn.setText('Play')
        #     self.playBtn.setEnabled(True)
        # if self.downldfile == self.audioName:
        #     pygame.mixer.music.load(self.downldfile)
        #     self.audioState = self.AUDIOREADY

    def parseRtspReply(self, data):
        """parse the RTSP reply from the server"""
        lines = str(data).split('\n')
        seqNum = int(lines[1].split(' ')[1])
        # print(lines)

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:
            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same
            if self.sessionId == session:
                if int(lines[0].split(' ')[1]) == 200:
                    if self.requestSent == self.SETUP:
                        self.state = self.READY
                        # Open RTP/RTCP port.
                        self.openRtpPort()
                        self.openRtcpPort()
                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                    elif self.requestSent == self.SPEED:
                        pass
                    elif self.requestSent == self.QUALITY:
                        pass
                    elif self.requestSent == self.REPOS:
                        self.state = self.PLAYING
                    elif self.requestSent == self.CHANGE:
                        self.frameTotal = int(float(lines[3].split(' ')[1]))
                        self.playSlider.setMaximum(self.frameTotal)
                        self.fps = float(lines[4].split(' ')[1])
                        self.timeLabel.setText(formatPlayTime(self.frameNbr, self.frameTotal, self.fps))
                        self.imgLabel.setPixmap(QPixmap('assets/paused.png'))
                        self.state = self.READY
                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY
                        # The play thread exits. A new thread is created on resume.
                        self.playEvent.set()
                    elif self.requestSent == self.TEARDOWN:
                        # print('recv teardown')
                        self.state = self.INIT
                        # Flag the teardownAcked to close the socket.
                        self.teardownAcked = 1
                    elif self.requestSent == self.DOWNLOAD:
                        self.filesize = int(lines[3].split(' ')[1])

                # server response code 400 means file not found
                elif int(lines[0].split(' ')[1]) == 400:
                    QMessageBox.information(self, 'Not found', 'Movie not found on server',
                                            QMessageBox.Close, QMessageBox.Close)

    def openRtpPort(self):
        """open RTP socket binded to a specified port"""
        # Create a new datagram socket to receive RTP packets from the server
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the timeout value of the socket to 0.5sec
        self.rtpSocket.settimeout(0.5)

        try:
            # Bind the socket to the address using the RTP port given by the client user
            self.rtpSocket.bind(("", self.rtpPort))
        except:
            QMessageBox.information(self, 'Unable to Bind', 'Unable to bind PORT=%d' % self.rtpPort,
                                    QMessageBox.Close, QMessageBox.Close)

    def openRtcpPort(self):
        """open RTCP socket binded to a specified port"""
        # Create a new datagram socket to receive RTP packets from the server
        self.rtcpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        try:
            # Bind the socket to the address using the RTP port given by the client user
            self.rtcpSocket.bind(("", self.rtcpPort))
        except:
            QMessageBox.information(self, 'Unable to Bind', 'Unable to bind PORT=%d' % self.rtcpPort,
                                    QMessageBox.Close, QMessageBox.Close)
        threading.Thread(target=self.listenRtcp).start()

    def closeEvent(self, event):
        """handler on explicitly closing the GUI window"""
        self.pauseMovie()
        reply = QMessageBox.information(
            self, "Quit?", "Are you sure you want to quit?",
            QMessageBox.Yes|QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.exitClient()
            event.accept()
        else:  # When the user presses cancel, resume playing.
            self.playMovie()
            event.ignore()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    client = Client(rtspport=sys.argv[1], ftpport=sys.argv[2], rtpport=sys.argv[3])

    sys.exit(app.exec_())
