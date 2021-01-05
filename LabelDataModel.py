# -*- coding: utf-8 -*-
import numpy as np
import cv2
import os
import lmdb
import sys
import six
import math


class ImagePatchData:

    def __init__(self, index, image, label):
        self._index = index
        self._image = image
        self._label = label

    @property
    def image(self):
        return self._image

    @property
    def label(self):
        return self._label

    @property
    def index(self):
        return self._index


def lmdb_put_image(txn, key, image):
    is_success, buffer = cv2.imencode('.jpg', image)
    if not is_success:
        print('convert image to byte buffer failed')
        return

    if not txn.put(key.encode(), buffer):
        print('write image data to lmdb failed')


def lmdb_put_text(txn, key, value):
    if not txn.put(key.encode(), value.encode()):
        print('cannot write text {}: {}'.format(key, value))
        sys.exit()


def lmdb_put_int(txn, key, value):
    if not txn.put(key.encode(), str(value).encode()):
        print('cannot write int {}: {}'.format(key, value))
        sys.exit()


def lmdb_get_txt(txn, key):
    value = txn.get(key.encode(), default=None)

    if value is not None:
        value = value.decode('utf-8')
    return value


def lmdb_get_int(txn, key):
    value = txn.get(key.encode(), default=None)

    if value is not None:
        value = value.decode('utf-8')
        value = int(value)
    return value


def lmdb_get_image(txn, key):
    bytes_image = txn.get(key.encode(), default=None)
    if bytes_image is None:
        return None

    io_buf = six.BytesIO(bytes_image)
    image = cv2.imdecode(np.frombuffer(io_buf.getbuffer(), np.uint8), -1)
    return image


def lmdb_get_label_key(index):
    return 'label-%09d' % index


def lmdb_get_image_key(index):
    return 'image-%09d' % index


def get_record_key(index):
    image_key = lmdb_get_image_key(index)
    label_key = lmdb_get_label_key(index)
    return image_key, label_key


class TextRecognitionImagePatchDataset:
    _n_samples: int

    def __init__(self, path=None, w_size=128, h_size=32, interpolation=cv2.INTER_CUBIC):
        self._lmdb = None
        self._n_samples = 0
        self._w_size = w_size
        self._h_size = h_size
        self._interpolation = interpolation

        if path is not None:
            self.connect_dataset(path)

    def connect_dataset(self, lmdb_path):
        if not os.path.exists(lmdb_path):
            print('can not find lmdb data: {}'.format(lmdb_path))
            return None

        # self._lmdb = lmdb.open(lmdb_path, max_readers=32, lock=False, readahead=False, meminit=False, create=False)
        self._lmdb = lmdb.open(lmdb_path, create=False, lock=True, map_size=100000000)
        if not self._lmdb:
            print('can not open lmdb from {}'.format(lmdb_path))
            return None

        with self._lmdb.begin(write=False) as txn:
            self._n_samples = lmdb_get_int(txn, 'num-samples')

        if self._n_samples is None or self._n_samples == 0:
            print('lmdb data set is empty')
            return None
        return True

    def get_label(self, index):
        if self._lmdb is None:
            print('you should open lmdb first before read data ')
            return None

        label_key = lmdb_get_label_key(index)
        with self._lmdb.begin(write=False) as txn:
            label = lmdb_get_txt(txn, label_key)
            return label

    def resize_image(self, image):
        height, width, channel = image.shape
        if height > width/2:
            ratio = width / float(height)
            if math.ceil(self._h_size * ratio) > self._w_size:
                resized_w = self._w_size
            else:
                resized_w = math.ceil(self._h_size * ratio)
            img = cv2.resize(image, (resized_w, self._h_size), self._interpolation)
            pad_img = np.zeros((self._h_size, self._w_size, 3), dtype=np.uint8)
            pad_img[:, :resized_w, :] = img  # right pad
            if self._w_size != resized_w:  # add border Pad
                pad_img[:, resized_w:, :] = np.repeat(np.expand_dims(img[:, resized_w-1, :], 1),
                                                      self._w_size - resized_w, axis=1)
            return pad_img
        else:
            img = cv2.resize(image, (self._w_size, self._h_size), self._interpolation)
            return img

    def get_patch_list(self, count, start=1):
        if self._lmdb is None:
            print('you should open lmdb first before read data ')
            return None

        image_patch_list = []
        end = min(start + count, self._n_samples)
        with self._lmdb.begin(write=False) as txn:
            for i in range(start, end):
                image_key, label_key = get_record_key(i)
                im = lmdb_get_image(txn, image_key)
                # im = self.resize_image(im)
                # im = cv2.resize(im, (128, 32))
                label = lmdb_get_txt(txn, label_key)
                patch = ImagePatchData(i, im, label)
                image_patch_list.append(patch)

        return image_patch_list

    @property
    def patch_count(self):
        return self._n_samples

    def set_label(self, index, label):
        if self._lmdb is None:
            print('you should open lmdb first before read data ')
            return None

        label_key = lmdb_get_label_key(index)
        with self._lmdb.begin(write=True) as txn:
            lmdb_put_text(txn, label_key, label)

    def set_deleted_mark(self, index):
        self.set_label(index, '__#TO_BE_DELETED#__')


if __name__ == "__main__":
    dataset = TextRecognitionImagePatchDataset('D:\\\\data\\ocr_lmdb_2\\train')
    samples = dataset.get_patch_list(10, 1)
    for sample in samples:
        cv2.imshow('{}:{}'.format(sample.index, sample.label), sample.image)
        cv2.waitKey(0)
