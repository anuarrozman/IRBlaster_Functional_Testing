#!/usr/bin/python3
# -*-coding:Utf-8 -*

import sys,os, time
import platform
from random import randint
import serial,serial.tools.list_ports

#interface import
from PySide2.QtWidgets import QApplication, QMainWindow,QDesktopWidget, QTextEdit, QLineEdit, QPushButton, QMessageBox, QWidget, QGridLayout, QTextEdit, QGroupBox, QVBoxLayout,QHBoxLayout, QComboBox, QLabel
from PySide2.QtGui import QIcon, QScreen

class SerialInterface(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.width=650
        self.height=350
        
        self.resize(self.width, self.height)
        self.setWindowIcon(QIcon('./resources/logo-100.png'))
        self.setWindowTitle( 'Serial Monitor')
        
        #center window on screen
        qr = self.frameGeometry()
        cp = QScreen().availableGeometry().center()
        qr.moveCenter(cp)
        
        
        #init layout
        centralwidget = QWidget(self)
        centralLayout=QHBoxLayout(centralwidget)
        self.setCentralWidget(centralwidget)
        
        #add connect group
        #self.connectgrp=GroupClass(self)
        #centralLayout.addWidget(self.connectgrp)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    frame = SerialInterface()
    frame.show()
    sys.exit(app.exec_())