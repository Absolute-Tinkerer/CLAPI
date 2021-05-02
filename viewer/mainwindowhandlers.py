# -*- coding: utf-8 -*-
"""
Created on Sat May  1 18:36:09 2021

@author: The Absolute Tinkerer
"""

import os
import sys
import subprocess

from PyQt5.QtWidgets import QMainWindow, QLabel, QTextEdit, QPushButton
from PyQt5.QtGui import QPixmap

from .MainWindowUI import Ui_MainWindow


class MainWindowHandlers(QMainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindowHandlers, self).__init__(*args, **kwargs)

        ui = Ui_MainWindow()
        ui.setupUi(self)

    def initialize(self, posts):
        self._posts = posts

        self._textfield = self.findChild(QTextEdit, 'postTextEdit')
        self._recnumLabel = self.findChild(QLabel, 'recnumLabel')
        self._imgnumLabel = self.findChild(QLabel, 'imgnumLabel')
        self._imgLabel = self.findChild(QLabel, 'imgLabel')
        self._pimgBtn = self.findChild(QPushButton, 'prevImgBtn')
        self._nimgBtn = self.findChild(QPushButton, 'nextImgBtn')

        # Post and image index and count
        self._pidx = 0
        self._iidx = 0

        # Load the first post
        self._loadPost(self._posts[self._pidx])

    def nextImage(self):
        post = self._posts[self._pidx]
        self._iidx = (self._iidx + 1) % len(post.image_urls)
        self._setImage('tmp/%s_%s.jpg' % (post.pid, self._iidx))

    def nextPost(self):
        self._pidx = (self._pidx + 1) % len(self._posts)
        self._iidx = 0
        self._loadPost(self._posts[self._pidx])

    def previousImage(self):
        post = self._posts[self._pidx]
        self._iidx = (self._iidx - 1) % len(post.image_urls)
        self._setImage('tmp/%s_%s.jpg' % (post.pid, self._iidx))

    def previousPost(self):
        self._pidx = (self._pidx - 1) % len(self._posts)
        self._iidx = 0
        self._loadPost(self._posts[self._pidx])

    def openPost(self):
        post = self._posts[self._pidx]
        subprocess.call('chrome.exe %s -incognito --new-window' % post.url)

    def openMap(self):
        post = self._posts[self._pidx]
        subprocess.call('chrome.exe %s -incognito --new-window' % post.gps)

    def _setImage(self, path=None):
        if path is None:
            path = os.path.abspath(
                       sys.modules[MainWindowHandlers.__module__].__file__)
            path = os.path.abspath(os.path.join(path, '..', 'placeholder.jpg'))
        else:
            if not os.path.exists(path):
                path = os.path.abspath(
                    sys.modules[MainWindowHandlers.__module__].__file__)
                path = os.path.abspath(os.path.join(path, '..', 'online.jpg'))
            self._imgnumLabel.setText('(%+3s/%+3s)' % (
                self._iidx+1, len(self._posts[self._pidx].image_urls)))

        pixmap = QPixmap(path)
        self._imgLabel.setPixmap(pixmap)

    def _loadPost(self, post):
        # Load the image
        if len(post.image_urls) > 0:
            self._setImage('tmp/%s_0.jpg' % post.pid)
            self._pimgBtn.setEnabled(True)
            self._nimgBtn.setEnabled(True)
        else:
            self._setImage()
            self._pimgBtn.setEnabled(False)
            self._nimgBtn.setEnabled(False)

        # Set the text label values
        self._recnumLabel.setText('(%+3s/%+3s)' % (
            self._pidx+1, len(self._posts)))

        # Set the text field contents
        s = '%s\n' % post.hood
        s += '%s\n' % post.text
        s += '$%s\n' % post.price
        s += '\nReference URL: %s' % post.url
        self._textfield.setPlainText(s)
