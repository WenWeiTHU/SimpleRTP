#!/usr/bin/env python
# -*- coding: UTF8 -*-
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *


class ConfigDialog(QDialog):
    def __init__(self, parent=None):
        super(ConfigDialog, self).__init__(parent)

        self.contentsWidget = QListWidget()
        self.contentsWidget.setViewMode(QListView.IconMode)
        self.contentsWidget.setIconSize(QSize(96, 84))  # Icon 大小
        self.contentsWidget.setMovement(QListView.Static)  # Listview显示状态
        self.contentsWidget.setMaximumWidth(800)  # 最大宽度
        self.contentsWidget.setSpacing(12)  # 间距大小
        self.createIcons()
        horizontalLayout = QHBoxLayout()
        horizontalLayout.addWidget(self.contentsWidget)
        mainLayout = QVBoxLayout()
        mainLayout.addLayout(horizontalLayout)
        self.setLayout(mainLayout)
        self.resize(300, 300)

    def createIcons(self):
        configButton = QListWidgetItem(self.contentsWidget)
        configButton.setIcon(QIcon('image/paused.png'))
        configButton.setText("Configuration")
        configButton.setTextAlignment(Qt.AlignHCenter)
        configButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        updateButton = QListWidgetItem(self.contentsWidget)
        updateButton.setIcon(QIcon('image/paused.png'))
        updateButton.setText("Updatessss")
        updateButton.setTextAlignment(Qt.AlignHCenter)
        updateButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        queryButton = QListWidgetItem(self.contentsWidget)
        queryButton.setIcon(QIcon('image/paused.png'))
        queryButton.setText("Query")
        queryButton.setTextAlignment(Qt.AlignHCenter)
        queryButton.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.contentsWidget.currentItemChanged.connect(self.changePage)

    # QListWidget current 改变时触发
    def changePage(self, current, previous):
        print(self.contentsWidget.row(current))


if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)
    dialog = ConfigDialog()
    dialog.show()
    sys.exit(dialog.exec_())