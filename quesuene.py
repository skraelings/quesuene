#!/usr/bin/env python2

import re
import subprocess
from operator import itemgetter

from PyQt5 import Qt
from PyQt5 import QtCore

APP_STYLE = """
VolumeWidget {
    background-color: rgba(0, 0, 0, 140);
}

QSlider::groove:horizontal {
    background: #F1F1F5;
    height: 5px;
    border-radius: 4px;
}

QSlider::sub-page:horizontal {
    background: #47A6E6;
    border: 1px solid #777;
}

QSlider::add-page:horizontal {
    border: 2px solid #777;
    height: 1px;
}

QSlider::handle:horizontal {
    background: #F0F1F5;
    border: 1px none;
    width: 9px;
    margin-top: -2px;
    margin-bottom: -2px;
    border-radius: 3px;
}

QLabel {
    color: white;
}
"""

def list_sink_inputs():
    """Returns a list where each item is a dictionary of parameters from the
    sink-input. More recently created sink-inputs come first."""

    def _parse(data):
        index = re.findall("Sink Input #([0-9]*)", data)[0]
        app_name = re.findall("application.name = \"(.*)\"", data)[0]
        volume_l, volume_r = re.findall("([0-9]*%)", data)
        assert volume_r == volume_l, "Volume level on left and right are not the same"
        return {"index":index, "app_name":app_name, "volume":volume_l}

    def parse_command_output(command_output):
        return [_parse(sink_input)
                for sink_input in re.split("\n\n", command_output)
                if sink_input]

    command_ouput = subprocess.check_output(["pactl", "list", "sink-inputs"])
    sink_inputs = parse_command_output(command_ouput)
    return sorted(sink_inputs, key=itemgetter('index'), reverse=True)


def set_sink_input_volume(sink_id, volume):
    subprocess.check_output(["pactl", "set-sink-input-volume", sink_id,
                             str(volume) + '%'])


class SinkInputWidget(Qt.QWidget):
    def __init__(self, sink_input, parent=None):
        super(SinkInputWidget, self).__init__(parent)
        self.sink_input = sink_input
        self.layout = Qt.QHBoxLayout()
        self.slider = Qt.QSlider(QtCore.Qt.Horizontal, self)
        self.slider.setValue(int(sink_input['volume'].strip('%')))
        self.slider.setSingleStep(1)
        self.slider.valueChanged.connect(self.handle_value_changed)
        slider_size_policy = Qt.QSizePolicy(Qt.QSizePolicy.Preferred,
                                     Qt.QSizePolicy.Expanding)
        self.slider.setSizePolicy(slider_size_policy)
        self.slider.setFixedWidth(180)
        label = Qt.QLabel(self.sink_input['app_name'], self)
        label.setFont(Qt.QFont(u'Sans Serif', 11))
        self.layout.addWidget(label)
        self.layout.addWidget(self.slider)
        self.setLayout(self.layout)

    def handle_value_changed(self, volume):
        set_sink_input_volume(self.sink_input['index'], volume)

    def sizeHint(self):
        return Qt.QSize(300, 15)


class VolumeWidget(Qt.QWidget):
    def __init__(self, parent=None):
        super(VolumeWidget, self).__init__(parent)
        # taskbarless and frameless
        self.setWindowFlags(QtCore.Qt.Tool | QtCore.Qt.FramelessWindowHint)
        # for true transparency enable composition in your WM
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setAttribute(QtCore.Qt.WA_NoSystemBackground, False)
        # Since we set flag Popup make explicit that we want to quit when
        # close. See the following
        # The QApplication::lastWindowClosed() signal is emitted when the last
        # visible primary window (i.e. window with no parent) with the
        # Qt::WA_QuitOnClose attribute set is closed. By default this attribute
        # is set for all widgets except transient windows such as splash
        # screens, tool windows, and popup menus.
        self.setAttribute(QtCore.Qt.WA_QuitOnClose, True)

        # stack each slider nicely
        sink_inputs_layout = Qt.QVBoxLayout()
        for sink_input in list_sink_inputs():
            siw = SinkInputWidget(sink_input, parent=self)
            sink_inputs_layout.addWidget(siw)
            # but we also want to restart the timer if any activity is detected
            siw.slider.valueChanged.connect(
                self.handle_timer_restart)
        self.setLayout(sink_inputs_layout)

        # close automatically when timer expires
        self.timer = Qt.QTimer(self)
        self.timer.timeout.connect(self.close)
        self.timer.start(3000)

    def handle_timer_restart(self):
        self.timer.start(1500)


if __name__ == "__main__":
    import os
    import sys
    # style sheet for whole app
    app = Qt.QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    volume_control = VolumeWidget()
    # center the damn thin'
    volume_control.adjustSize()
    volume_control.move(Qt.QApplication.desktop().screen().rect().center() -
                        volume_control.rect().center())
    volume_control.show()
    app.exec_()
