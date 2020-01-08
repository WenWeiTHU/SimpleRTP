from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class PlayPauseSignals(QObject):
    playPause = pyqtSignal()

class changePosSignals(QObject):
    changePos = pyqtSignal()


class FileSignals(QObject):
    filename = pyqtSignal(str)

class QMovieLabel(QLabel):
    """Extented clickeble label for play a videp"""
    def __init__(self):
        super(QMovieLabel, self).__init__()
        self.playPauseSig = PlayPauseSignals()


    def mousePressEvent(self, event):
        self.playPauseSig.playPause.emit()

class QMovieSlider(QSlider):
    def __init__(self, *args):
        super(QMovieSlider, self).__init__(*args)
        self.rePosSig = changePosSignals()

    def mousePressEvent(self, ev):
        pos = ev.pos().x() / self.width()
        self.setValue(pos * (self.maximum() - self.minimum()) + self.minimum())
        self.rePosSig.changePos.emit()
        return super().mousePressEvent(ev)


class RemoteFileWidget(QListWidget):
    """A list-like widget with menu action for file demonstration"""
    def __init__(self):
        super(RemoteFileWidget, self).__init__()
        self.fileMenu = QMenu(self)
        self.fileSignals = FileSignals()
        self.downldSignals = FileSignals()
        self.selectedName = ''
        self.setViewMode(QListView.IconMode)
        self.setIconSize(QSize(240, 135))  #
        self.setSpacing(4)  #
        self.fileMenu.addAction(QAction('Play', self,
                                        triggered=lambda: self.fileSignals.filename.emit(self.selectedName)))
        self.fileMenu.addAction(QAction('Download', self,
                                        triggered=lambda: self.downldSignals.filename.emit(self.selectedName)))

    def mousePressEvent(self, event):
        super(RemoteFileWidget, self).mousePressEvent(event)
        if event.button() == Qt.RightButton:
            item = self.indexAt(self.viewport().mapFromGlobal(QCursor.pos()))
            self.showMenu(item)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.indexAt(self.viewport().mapFromGlobal(QCursor.pos()))
            if item.data():
                self.selectedName = item.data()
                if item.data():
                    self.fileSignals.filename.emit(self.selectedName)

    def showMenu(self, item):
        if item.data():
            self.selectedName = item.data()
            self.fileMenu.exec_(QCursor.pos())
