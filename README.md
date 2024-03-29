PyVisualizer

============

Based off of code at:
https://github.com/ajalt/PyVisualizer

A simple music visualizer written in python and Qt.



Binary Installation
===================
The compiled binaries can be used without installation.

Running from Source
===================
Install the following dependencies:
<table>
<tr><td>Python 2.7</td><td>http://www.python.org/download/</td></tr>
<tr><td>NumPy</td><td>http://www.scipy.org/Download</td></tr>
<tr><td>PySide</td><td>http://qt-project.org/wiki/PySideDownloads</td></tr>
<tr><td>PySide-QtMultimedia</td><td>Included in the PySide binaries on Windows and OSX</td></tr>
</table>

The program can be run with `python main.py`

Usage
=====
The visualizer uses sound from your microphone to generate the visuals,
so make sure your microphone is working.

Controls
--------
<table>
<tr><td>Esc</td><td>Enter and exit full screen mode</td></tr>
<tr><td>S</td><td>Toggle showing or hiding statistics</td></tr>
<tr><td>R</td><td>Toggle rolling averages for amplitude and frequency</td></tr>
<tr><td>+/-</td><td>Increase or decrease rolling average learning rate</td></tr>
</table>

