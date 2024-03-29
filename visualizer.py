"""Module that contains visualizer classes."""

import sys
import random
import time
import math

import numpy as np
from PySide import QtCore, QtGui
from PySide.QtCore import QPointF, Qt, QPoint

SAMPLE_MAX = 32767
SAMPLE_MIN = -(SAMPLE_MAX + 1)
SAMPLE_RATE = 44100  # [Hz]
NYQUIST = SAMPLE_RATE / 2
SAMPLE_SIZE = 16  # [bit]
CHANNEL_COUNT = 1
BUFFER_SIZE = 5000


class Visualizer(QtGui.QLabel):
    """The base class for visualizers.
    
    When initializing a visualizer, you must provide a get_data function which
    takes no arguments and returns a NumPy array of PCM samples that will be
    called exactly once each time a frame is drawn.
    
    Note: Although this is an abstract class, it cannot have a metaclass of
    abcmeta since it is a child of QObject.
    """

    def __init__(self, get_data, update_interval=33):
        super(Visualizer, self).__init__()

        self.get_data = get_data
        self.update_interval = update_interval  # 33ms ~= 30 fps
        self.sizeHint = lambda: QtCore.QSize(800, 800)
        self.setStyleSheet('background-color: black;');
        self.setWindowTitle('PyVisualizer')

    def show(self):
        """Show the label and begin updating the visualization."""
        super(Visualizer, self).show()
        self.refresh()

    def refresh(self):
        """Generate a frame, display it, and set queue the next frame"""
        data = self.get_data()
        interval = self.update_interval
        if data is not None:
            t1 = time.clock()
            self.setPixmap(QtGui.QPixmap.fromImage(self.generate(data)))
            # decrease the time till next frame by the processing tmie so that the framerate stays consistent
            interval -= 1000 * (time.clock() - t1)
        if self.isVisible():
            QtCore.QTimer.singleShot(self.update_interval, self.refresh)

    def generate(self, data):
        """This is the abstract function that child classes will override to
        draw a frame of the visualization.
        
        The function takes an array of data and returns a QImage to display"""
        raise NotImplementedError()


class LineVisualizer(Visualizer):
    """This visualizer will display equally sized rectangles
    alternating between black and another color, with the height of the
    rectangles determined by frequency, and the quantity of colored rectanges
    influnced by amplitude.
    """

    def __init__(self, get_data, columns=1):
        super(LineVisualizer, self).__init__(get_data)

        self.columns = columns
        self.brushes = [QtGui.QBrush(QtGui.QColor(255, 255, 255)),  # white
                        QtGui.QBrush(QtGui.QColor(255, 0, 0)),  # red
                        QtGui.QBrush(QtGui.QColor(0, 240, 0)),  # green
                        QtGui.QBrush(QtGui.QColor(0, 0, 255)),  # blue
                        QtGui.QBrush(QtGui.QColor(255, 255, 0)),  # yellow
                        QtGui.QBrush(QtGui.QColor(0, 255, 255)),  # teal
                        ]
        self.brush = self.brushes[0]

        self.display_odds = True
        self.display_evens = True
        self.is_fullscreen = False

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_I:
            self.display_evens = True
            self.display_odds = True
        elif event.key() == QtCore.Qt.Key_O:
            self.display_evens = True
            self.display_odds = False
        elif event.key() == QtCore.Qt.Key_P:
            self.display_evens = False
            self.display_odds = True
            return
        elif event.key() == QtCore.Qt.Key_Escape:
            if self.is_fullscreen:
                self.showNormal()
                self.is_fullscreen = False
            else:
                self.showFullScreen()
                self.is_fullscreen = True
        else:
            # Qt.Key enum helpfully defines most keys as their ASCII code,
            #   so we can use ord('Q') instead of Qt.Key.Key_Q
            color_bindings = dict(zip((ord(i) for i in 'QWERTYU'), self.brushes))
            try:
                self.brush = color_bindings[event.key()]
            except KeyError:
                if QtCore.Qt.Key_0 == event.key():
                    self.columns = 10
                elif QtCore.Qt.Key_1 <= event.key() <= QtCore.Qt.Key_9:
                    self.columns = event.key() - QtCore.Qt.Key_1 + 1

    def generate(self, data):
        fft = np.absolute(np.fft.rfft(data, n=len(data)))
        freq = np.fft.fftfreq(len(fft), d=1. / SAMPLE_RATE)
        max_freq = abs(freq[fft == np.amax(fft)][0])
        max_amplitude = np.amax(data)

        rect_width = int(self.width() / (self.columns * 2))

        freq_cap = 20000.  # this determines the scale of lines
        if max_freq >= freq_cap:
            rect_height = 1
        else:
            rect_height = int(self.height() * max_freq / freq_cap)
            if rect_height == 2: rect_height = 1

        img = QtGui.QImage(self.width(), self.height(), QtGui.QImage.Format_RGB32)
        img.fill(0)  # black

        if rect_height >= 1:
            painter = QtGui.QPainter(img)
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(self.brush)

            for x in xrange(0, self.width() - rect_width, rect_width * 2):
                for y in xrange(0, self.height(), 2 * rect_height):
                    if random.randint(0, int(max_amplitude / float(SAMPLE_MAX) * 10)):
                        if self.display_evens:
                            painter.drawRect(x, y, rect_width, rect_height)
                        if self.display_odds:
                            painter.drawRect(x + rect_width, self.height() - y - rect_height, rect_width, rect_height)

            del painter  #

        return img


class Spectrogram(Visualizer):
    def generate(self, data):
        fft = np.absolute(np.fft.rfft(data, n=len(data)))
        freq = np.fft.fftfreq(len(fft), d=1. / SAMPLE_RATE)
        max_freq = abs(freq[fft == np.amax(fft)][0]) / 2
        max_amplitude = np.amax(data)

        bins = np.zeros(200)
        # indices = (len(fft) - np.logspace(0, np.log10(len(fft)), len(bins), endpoint=False).astype(int))[::-1]
        # for i in xrange(len(bins) - 1):
        #    bins[i] = np.mean(fft[indices[i]:indices[i+1]]).astype(int)
        # bins[-1] = np.mean(fft[indices[-1]:]).astype(int)

        step = int(len(fft) / len(bins))
        for i in xrange(len(bins)):
            bins[i] = np.mean(fft[i:i + step])

        img = QtGui.QImage(self.width(), self.height(), QtGui.QImage.Format_RGB32)
        img.fill(0)
        painter = QtGui.QPainter(img)
        painter.setPen(QtCore.Qt.NoPen)
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))  # white)

        for i, bin in enumerate(bins):
            height = self.height() * bin / float(SAMPLE_MAX) / 10
            width = self.width() / float(len(bins))
            painter.drawRect(i * width, self.height() - height, width, height)

        del painter

        return img


class CustomVisualizer(Visualizer):
    def __init__(self, get_data, columns=1):
        super(CustomVisualizer, self).__init__(get_data)

        self.columns = columns
        self.brushes = [QtGui.QBrush(QtGui.QColor(255, 255, 255)),  # white
                        QtGui.QBrush(QtGui.QColor(255, 0, 0)),  # red
                        QtGui.QBrush(QtGui.QColor(0, 240, 0)),  # green
                        QtGui.QBrush(QtGui.QColor(0, 0, 255)),  # blue
                        QtGui.QBrush(QtGui.QColor(255, 255, 0)),  # yellow
                        QtGui.QBrush(QtGui.QColor(0, 255, 255)),  # teal
                        ]
        self.brush = self.brushes[0]

        # custom constants
        self.ampl_range = (1000, 100)  # (lower bound, spectrum width)
        self.freq_range = (1000, 100) # (lower bound, spectrum width)
        self.max_points = 128

        self.inner_rad = 50
        self.inner_circ = 2 * math.pi * self.inner_rad
        self.outer_rad = 400
        self.outer_circ = 2 * math.pi * self.outer_rad
        self.center = (400, 400)

        self.rollingAmpl = 80
        self.rollingFreq = 300
        self.amplLearningRate = 0.90
        self.freqLearningRate = 0.90
        # end custom constants

        self.use_rolling = False
        self.display_stats = False
        self.is_fullscreen = False


    def __getDecimalRange__(self, val, isAmpl):
        if isAmpl:
            valRatio = (val - self.ampl_range[0]) / self.ampl_range[1]
            if valRatio > 1:
                self.ampl_range = (self.ampl_range[0], val - self.ampl_range[0])
            elif valRatio < 0:
                self.ampl_range = (val, self.ampl_range[1])
        else:
            valRatio = (val - self.freq_range[0]) / self.freq_range[1]
            if valRatio > 1:
                self.freq_range = (self.freq_range[0], val - self.freq_range[0])
            elif valRatio < 0:
                self.freq_range = (val, self.freq_range[1])

        return valRatio


    def __getStarPoints__(self, points):
        """

        :param points: Int
        :return: [Array-of QPointF]
        """

        star = QtGui.QPolygon()

        for point in range(0, points):
            point1, point2 = self.__getStarPair__(points, point)
            star.append(point1)
            star.append(point2)

        return star

    def __getStarPair__(self, points, idx):
        """

        :param points: int
        :param idx: int
        :return: QPointF, QPointF
        """
        inner_angle = float(idx) / points * 2 * math.pi
        outer_angle = float(idx) / points * 2 * math.pi + math.pi / points
        inner_x = self.inner_rad * math.cos(inner_angle) + self.center[0]
        inner_y = self.inner_rad * math.sin(inner_angle) + self.center[1]
        outer_x = self.outer_rad * math.cos(outer_angle) + self.center[0]
        outer_y = self.outer_rad * math.sin(outer_angle) + self.center[1]

        inner_point = QPoint(inner_x, inner_y)
        outer_point = QPoint(outer_x, outer_y)

        return inner_point, outer_point

    def __getColor__(self, val):
        """

        :param ampl: Float
        :return: QBrush
        """
        colVal =  self.__getDecimalRange__(val, False)
        pastHalf = colVal > 0.5

        color = (colVal - 0.5) * 2 if pastHalf else colVal * 2

        color = color * 255

        if color < 0:
            color = 0

        if color > 255:
            color = 255

        if pastHalf:
            return QtGui.QBrush(QtGui.QColor(color, 255 - color, 0))
        else:
            return QtGui.QBrush(QtGui.QColor(0, color, 255 - color))


    def __getPoints__(self, val):
        points = self.__getDecimalRange__(val, True) * self.max_points

        if points < 2:
            points = 2

        if points > self.max_points:
            points = self.max_points

        return self.__getStarPoints__(int(points))


    def __updateMaximums__(self):
        self.ampl_range = (self.ampl_range[0], self.ampl_range[1] * 0.999)
        self.freq_range = (self.freq_range[0], self.freq_range[1] * 0.999) 


    def __updateRolling__(self, max_amplitude, max_freq):
        self.rollingAmpl = self.rollingAmpl * self.amplLearningRate + max_amplitude * (1 - self.amplLearningRate)
        self.rollingFreq = self.rollingFreq * self.freqLearningRate + max_freq * (1 - self.freqLearningRate)


    def __drawStats__(self, painter, max_amplitude, max_freq):
        painter.setBrush(QtGui.QBrush(QtGui.QColor(255, 255, 255)))
        topLeftRect = QtCore.QRect(0, 0, 200, 50)
        topRightRect = QtCore.QRect(self.width() - 200, 0, 200, 50)
        topLeftText = QtCore.QRect(10, 5, 180, 40)
        topRightText = QtCore.QRect(self.width() - 190, 5, 180, 40)
        painter.drawRect(topLeftRect)
        painter.drawRect(topRightRect)

        painter.setFont(QtGui.QFont('Decorative', 10))
        painter.drawText(topLeftText, Qt.AlignLeft | Qt.AlignVCenter, "Amplitude") 
        painter.drawText(topLeftText, Qt.AlignRight | Qt.AlignVCenter, getTrimString(max_amplitude)) 
        painter.drawText(topRightText, Qt.AlignLeft | Qt.AlignVCenter, "Frequency") 
        painter.drawText(topRightText, Qt.AlignRight | Qt.AlignVCenter, getTrimString(max_freq))


        bottomLeftRect = QtCore.QRect(0, self.height() - 70, 250, 70)
        bottomLeftText = QtCore.QRect(10, self.height() - 65, 230, 60)
        painter.drawRect(bottomLeftRect)
        painter.drawText(bottomLeftText, Qt.AlignLeft | Qt.AlignTop, "Ampl") 
        painter.drawText(bottomLeftText, Qt.AlignHCenter | Qt.AlignTop, getTrimString(self.ampl_range[0])) 
        painter.drawText(bottomLeftText, Qt.AlignRight | Qt.AlignTop, getTrimString(self.ampl_range[0] + self.ampl_range[1])) 
        painter.drawText(bottomLeftText, Qt.AlignLeft | Qt.AlignBottom, "Freq") 
        painter.drawText(bottomLeftText, Qt.AlignHCenter | Qt.AlignBottom, getTrimString(self.freq_range[0]))
        painter.drawText(bottomLeftText, Qt.AlignRight | Qt.AlignBottom, getTrimString(self.freq_range[1] + self.freq_range[0]))


        if (self.use_rolling):
            bottomRightRect = QtCore.QRect(self.width() - 200, self.height() - 50, 200, 50)
            bottomRightText = QtCore.QRect(self.width() - 190, self.height() - 45, 180, 40)
            painter.drawRect(bottomRightRect)
            painter.drawText(bottomRightText, Qt.AlignLeft | Qt.AlignVCenter, "Learning Rate")
            painter.drawText(bottomRightText, Qt.AlignRight | Qt.AlignVCenter, str(self.amplLearningRate))


    def generate(self, data):
        fft = np.absolute(np.fft.rfft(data, n=len(data)))
        freqs = np.fft.fftfreq(len(fft), d=1. / SAMPLE_RATE)
        max_freq = abs(freqs[fft == np.amax(fft)][0])
        max_amplitude = np.amax(data)

        self.__updateRolling__(max_amplitude, max_freq)
        self.__updateMaximums__()
        
        if self.use_rolling:
            ampl = self.rollingAmpl
            freq = self.rollingFreq
        else:
            ampl = max_amplitude
            freq = max_freq


        brush = self.__getColor__(freq)
        star_points = self.__getPoints__(ampl)

        # ----------------------------------------------------------------------------- #

        img = QtGui.QImage(self.width(), self.height(), QtGui.QImage.Format_RGB32)
        img.fill(0)  # black

        painter = QtGui.QPainter(img)

        if self.display_stats:
            self.__drawStats__(painter, ampl, freq)
        

        painter.setBrush(brush)
        painter.drawPolygon(star_points, fill_rule=Qt.FillRule.WindingFill)
        del painter  #

        return img

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_S:
            self.display_stats = not self.display_stats
        elif event.key() == QtCore.Qt.Key_R:
            self.use_rolling = not self.use_rolling
        elif event.key() == QtCore.Qt.Key_Equal:
            if (self.amplLearningRate < 0.99):
                self.amplLearningRate += 0.01
                self.freqLearningRate += 0.01
        elif event.key() == QtCore.Qt.Key_Minus:
            if (self.amplLearningRate > 0.01):
                self.amplLearningRate -= 0.01
                self.freqLearningRate -= 0.01
        elif event.key() == QtCore.Qt.Key_Escape:
            if self.is_fullscreen:
                self.showNormal()
                self.is_fullscreen = False
            else:
                self.showFullScreen()
                self.is_fullscreen = True
            self.center = (self.width() / 2, self.height() / 2)
        else:
            # Qt.Key enum helpfully defines most keys as their ASCII code,
            #   so we can use ord('Q') instead of Qt.Key.Key_Q
            color_bindings = dict(zip((ord(i) for i in 'QWERTYU'), self.brushes))
            try:
                self.brush = color_bindings[event.key()]
            except KeyError:
                if QtCore.Qt.Key_0 == event.key():
                    self.columns = 10
                elif QtCore.Qt.Key_1 <= event.key() <= QtCore.Qt.Key_9:
                    self.columns = event.key() - QtCore.Qt.Key_1 + 1


def getTrimString(num):
    numString = str(num)
    decimalSpot = numString.index(".")
    return numString[0:decimalSpot + 2]