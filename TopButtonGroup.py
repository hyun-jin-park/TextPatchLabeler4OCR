from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel, QApplication, QFileDialog
from PyQt5.QtCore import Qt
from Controller import Controller


class TopButtonGroup(QWidget):
    def __init__(self, controller):
        super().__init__()
        self._position_label = QLabel()
        self._open_button = QPushButton('Open')
        self._next_button = QPushButton('Next')
        self._prev_button = QPushButton('Prev')
        self._controller = controller

        self._current_path = None

        self.init_ui()

    def init_ui(self):
        layout = QHBoxLayout()
        layout.addWidget(self._position_label)
        layout.addWidget(self._open_button)
        layout.addWidget(self._prev_button)
        layout.addWidget(self._next_button)
        self.setLayout(layout)

        self._open_button.clicked.connect(self.open_image)
        self._next_button.clicked.connect(self.next_image)
        self._prev_button.clicked.connect(self.prev_image)

    def open_image(self):
        open_file_info = QFileDialog.getExistingDirectory(self, 'select lmdb database folder', './',
                                                          options=QFileDialog.ShowDirsOnly)
        if open_file_info is not None and open_file_info != "":
            self._current_path = open_file_info
            self._controller.open_lmdb(self._current_path, 1)
        self._position_label.setText(self._controller.get_status_text())
        QApplication.restoreOverrideCursor()

    def next_image(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._controller.next_patch()
        self._position_label.setText(self._controller.get_status_text())
        QApplication.restoreOverrideCursor()

    def prev_image(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._controller.prev_patch()
        self._position_label.setText(self._controller.get_status_text())
        QApplication.restoreOverrideCursor()

    def update(self):
        self._position_label.setText(self._controller.get_status_text())


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    my_controller = Controller()
    form = TopButtonGroup(my_controller)
    form.show()
    app.exec_()
