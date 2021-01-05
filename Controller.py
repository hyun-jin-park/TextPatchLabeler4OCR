from LabelDataModel import TextRecognitionImagePatchDataset
import pickle
import os


class Bookmark:
    def __init__(self):
        self._lmdb_path = None
        self._lmdb_index = 0
        self._bookmark_path = '.bookmark'

        if os.path.exists(self._bookmark_path):
            with open(self._bookmark_path, 'rb') as f:
                self._lmdb_path = pickle.load(f)
                self._lmdb_index = pickle.load(f)
                self._lmdb_index = 1000000

    def update_all(self, path, index):
        self._lmdb_path = path
        self._lmdb_index = index
        with open(self._bookmark_path, 'wb') as f:
            pickle.dump(self._lmdb_path, f)
            pickle.dump(self._lmdb_index, f)

    def update_index(self, index):
        self._lmdb_index = index
        with open(self._bookmark_path, 'wb') as f:
            pickle.dump(self._lmdb_path, f)
            pickle.dump(self._lmdb_index, f)

    @property
    def index(self):
        return self._lmdb_index

    @property
    def lmdb_path(self):
        return self._lmdb_path


class Controller:
    def __init__(self, view=None, data=None):
        self._bookmark = Bookmark()
        self._patch_start_index = self._bookmark.index
        self._patch_image_count = 0
        self._view = view

        if data is None:
            self._data = TextRecognitionImagePatchDataset()
        else:
            self._data = data

    def load_bookmark(self):
        if self._bookmark.lmdb_path is not None:
            self.open_lmdb(self._bookmark.lmdb_path)

    def get_status_text(self):
        if self._bookmark.lmdb_path is None:
            return None
        else:
            return self._bookmark.lmdb_path + ': {}/{}'.format(self._patch_start_index, self._patch_image_count)

    def notify_label_change(self, index, label):
        self._data.set_label(index, label)

    def open_lmdb(self, lmdb_path, start_index=None):
        if self._data.connect_dataset(lmdb_path) is None:
            return None
        if start_index is not None:
            self._patch_start_index = start_index
        self._patch_image_count = self._data.patch_count
        if self._view is not None:
            self._view.update_image_patch(self._data.get_patch_list(self._view.image_patch_count,
                                                                    self._patch_start_index))
        else:
            print('Controller: open image')

        self._bookmark.update_all(lmdb_path, self._patch_start_index)

    def next_patch(self):
        if self._view is None:
            print('Controller: next patch')
            return

        if self._patch_start_index + self._view.image_patch_count > self._patch_image_count:
            self._patch_start_index = 0
        else:
            self._patch_start_index = self._patch_start_index + self._view.image_patch_count

        self._view.update_image_patch(self._data.get_patch_list(self._view.image_patch_count, self._patch_start_index))
        self._bookmark.update_index(self._patch_start_index)

    def prev_patch(self):
        if self._view is None:
            print('Controller: previous patch')
            return

        if self._patch_start_index - self._view.image_patch_count < 0:
            self._patch_start_index = self._patch_image_count - self._view.image_patch_count
        else:
            self._patch_start_index = self._patch_start_index - self._view.image_patch_count

        self._view.update_image_patch(self._data.get_patch_list(self._view.image_patch_count, self._patch_start_index))
        self._bookmark.update_index(self._patch_start_index)

    def notify_view_selected(self, index):
        pass
