import sys
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import QMessageBox

from ImagePatchLabelView import ImagePatchView
from TopButtonGroup import TopButtonGroup

from Controller import Controller


class LabelWindow(QWidget):
    def __init__(self, image_patch_count=6):
        super(QWidget, self).__init__()
        self._controller = Controller(self)
        self._top_button_group = TopButtonGroup(self._controller)
        self._image_patch_count = image_patch_count
        self._image_patch_view_list = [ImagePatchView(self._controller) for _ in range(0, image_patch_count)]
        self.init_ui()
        self._controller.load_bookmark()

    @property
    def image_patch_count(self):
        return self._image_patch_count

    def is_updated(self):
        for view in self._image_patch_view_list:
            if view.is_updated():
                return True
        return False

    def show_message(self, message):
        QMessageBox.about(self, 'message', message)

    def init_ui(self):
        self.setMinimumWidth(1440)
        self.setMinimumHeight(1280)

        main_layout = QVBoxLayout()
        body_layout = QGridLayout()
        main_layout.addWidget(self._top_button_group, alignment=Qt.AlignTop)
        main_layout.addLayout(body_layout, stretch=10)

        for i in range(0, self._image_patch_count):
            # row = int(i / 3)
            row = i
            # column = i % 3
            column = 1
            body_layout.addWidget(self._image_patch_view_list[i], row, column, alignment=Qt.AlignTop)
        self.setLayout(main_layout)

    def update_image_patch(self, patch_list):
        for index, patch in enumerate(patch_list):
            self._image_patch_view_list[index].set(patch.index, patch.image, patch.label)
        self._top_button_group.update()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    form = LabelWindow()
    form.show()
    app.exec_()
