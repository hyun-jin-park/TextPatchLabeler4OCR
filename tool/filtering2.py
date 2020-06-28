"""
width	height		width/height
182     22	        8.00
128	    32	        4.00
90	    46	        2.00
74	    56	        1.33
64	    64	        1.00
56	    74	        0.75
46	    90	        0.50
32	    128	        0.25
22	    182	        0.13
16      256         0.06
"""
import numpy as np
import lmdb
import os
import cv2
import sys
import six
import time
from numpy.core._multiarray_umath import ndarray


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


ratio_range = np.array([8.0, 4.0, 2.00, 1.33, 1.00, 0.75, 0.50, 0.25, 0.13, 0.06])
# resize_array = [(182, 22), (128, 32), (90, 46), (74, 56), (64, 64),
#                 (56, 74), (46, 90), (32, 128), (22, 182), (16, 256)]

resize_array = [(364, 44), (256, 64), (180, 92), (148, 112), (128, 128),
                 (112, 148), (92, 180), (64, 256), (44, 364), (32, 512)]



paths = ['processed\\lmdb' + str(resize).replace(' ', '_') for resize in resize_array]
lmdb_connections = []
lmdb_transactions = []
lmdb_indexes = np.zeros(len(paths), dtype=np.uint32)

for path in paths:
    os.makedirs(path, exist_ok=True)
    _lmdb = lmdb.open(path, map_size=10995117000, max_readers=32, lock=False, readahead=False,
              meminit=False, create=True)
    lmdb_connections.append(_lmdb)
    sub_txn = _lmdb.begin(write=True)
    lmdb_transactions.append(sub_txn)

lmdb_connection = lmdb.open('D:\\data\\ui_image_patch\\result\\lmdb', max_readers=32, lock=False, readahead=False,
                            meminit=False, create=False)

lmdb_garbage = lmdb.open('processed\\lmdb', map_size=10995117000, create=True)
lmdb_garbage_transaction = lmdb_garbage.begin(write=True)
garbage_count = 0

t0 = time.time()
with lmdb_connection.begin(write=False) as main_txn:
    n_samples = lmdb_get_int(main_txn, 'num-samples')
    for main_index in range(0, n_samples):

        if main_index % 1000 == 1:
            print('----------------{0} iteration {1:.1f}--------------'.format(main_index, time.time() - t0))
            for slot, n_samples in enumerate(lmdb_indexes):
                print('{0} {1} {2:0.1f}'.format(slot, n_samples, n_samples/main_index * 100))

            for idx, sub_txn in enumerate(lmdb_transactions):
                lmdb_put_int(sub_txn, 'num-samples', lmdb_indexes[idx])
                sub_txn.commit()
                lmdb_transactions[idx] = lmdb_connections[idx].begin(write=True)
            t0 = time.time()

        patch_image_key, patch_label_key = get_record_key(main_index)
        im = lmdb_get_image(main_txn, patch_image_key)
        label = lmdb_get_txt(main_txn, patch_label_key)

        im_height, im_width, _ = im.shape
        ratio = im_width/im_height

        label_len = len(label)
        if im_width / label_len < 5:
            garbage_image_key, garbage_label_key = get_record_key(garbage_count)
            lmdb_put_image(lmdb_garbage_transaction, garbage_image_key, im)
            lmdb_put_text(lmdb_garbage_transaction, garbage_label_key, label)
            garbage_count += 1
            if garbage_count % 1000 == 1:
                print('garbage sync')
                lmdb_put_int(lmdb_garbage_transaction,'num-samples', garbage_count)
                lmdb_garbage_transaction.commit()
                lmdb_garbage_transaction = lmdb_garbage.begin(write=True)
        else:
            slot = np.argmin(np.abs(ratio_range-ratio))
            sub_txn = lmdb_transactions[slot]
            sub_index = lmdb_indexes[slot]

            # with lmdb_slot.begin(write=True) as sub_txn:
            sub_image_key, sub_label_key = get_record_key(sub_index)
            # cv2.imshow('before', im)
            # cv2.waitKey()
            im = cv2.resize(im, resize_array[slot], cv2.INTER_CUBIC)
            # cv2.imshow('after', im)
            # cv2.waitKey()
            lmdb_put_image(sub_txn, sub_image_key, im)
            lmdb_put_text(sub_txn, sub_label_key, label)
            lmdb_indexes[slot] += 1

    for slot in enumerate(lmdb_indexes) :
        lmdb_slot = lmdb_transactions[slot]
        n_samples = lmdb_indexes[slot]
        with lmdb_slot.begin(write=True) as sub_txn:
            lmdb_put_int(sub_txn, 'num-samples', n_samples)
            print('{} {}'.format(slot, n_samples))

    for sub_txn in lmdb_connections:
        sub_txn.commit()
