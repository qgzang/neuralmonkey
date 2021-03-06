""" Implementation of the dataset class. """

# tests: lint, mypy

import random

import magic
import numpy as np

from neuralmonkey.logging import log
from neuralmonkey.readers.plain_text_reader import PlainTextFileReader


class Dataset(object):
    """ This class serves as collection for data series for particular
    encoders and decoders in the model. If it is not provided a parent
    dataset, it also manages the vocabularies inferred from the data.

    A data serie is either a list of strings or a numpy array.

    Attributes:

        series: Dictionary from the series name to the actual data.

        series_outputs: Output files for target series.

        random_seed: Random seed used for shuffling.

    """

    def __init__(self, name, series, series_outputs, random_seed=None):
        """
        Creates a dataset from the provided already preprocessed series of
        data.

        Args:

        """

        self.name = name
        self._series = series
        self.series_outputs = series_outputs
        self.random_seed = random_seed

        self._check_series_lengths()

    def _check_series_lengths(self):
        lengths = [len(v) for v in list(self._series.values())
                   if isinstance(v, list) or isinstance(v, np.ndarray)]

        if len(set(lengths)) > 1:
            err_str = ["{}: {}".format(s, len(self._series[s]))
                       for s in self._series]
            raise Exception("Lengths of data series must be equal. Instead: {}"
                            .format(", ".join(err_str)))


    @staticmethod
    def create_series(path, preprocess=lambda x: x):
        """ Loads a data serie from a file """
        log("Loading {}".format(path))
        file_type = magic.from_file(path, mime=True).decode()

        if file_type.startswith('text/'):
            reader = PlainTextFileReader(path)
            return list([preprocess(line) for line in reader.read()])

        elif file_type == 'application/octet-stream':
            return np.load(path)
        else:
            raise Exception("\"{}\" has Unsupported data type: {}"
                            .format(path, file_type))


    def __len__(self):
        # type: () -> int
        if not list(self._series.values()):
            return 0
        else:
            return len(list(self._series.values())[0])

    def has_series(self, name):
        # type: (str) -> bool
        return name in self._series

    def get_series(self, name, allow_none=False):
        if allow_none:
            return self._series.get(name)
        else:
            return self._series[name]

    def shuffle(self):
        # type: () -> None
        """ Shuffles the dataset randomly """

        keys = list(self._series.keys())
        zipped = list(zip(*[self._series[k] for k in keys]))
        random.shuffle(zipped)
        for key, serie in zip(keys, list(zip(*zipped))):
            self._series[key] = serie

    def batch_serie(self, serie_name, batch_size):
        """ Splits a data serie into batches """
        buf = []
        for item in self.get_series(serie_name):
            buf.append(item)
            if len(buf) >= batch_size:
                yield buf
                buf = []
        if buf:
            yield buf

    def batch_dataset(self, batch_size):
        """ Splits the dataset into a list of batched datasets. """
        keys = list(self._series.keys())
        batched_series = [self.batch_serie(key, batch_size) for key in keys]

        batch_index = 0
        for next_batches in zip(*batched_series):
            batch_dict = {key:data for key, data in zip(keys, next_batches)}
            dataset = Dataset(self.name + "-batch-{}".format(batch_index), batch_dict, {})
            batch_index += 1
            yield dataset

