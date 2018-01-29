"""
PathElement class, use to represent path entries
"""

import datetime
import os
import logging

from .util import parse_rfc3339
from const import *

class PathElement(object):
    """ Path elements - we synchronize these
    """
    def __init__(self, path, time_stamp=0, size=0, is_directory=False, is_local=True):
        self.init(path, time_stamp, size, is_directory, is_local)

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def init(self, path, time_stamp, size, is_directory, is_local):
        """ Initialize a PathElement
        """
        self.path = path
        self.time_stamp = time_stamp
        self.size = size
        self.is_directory = is_directory
        self.is_local = is_local

    def contains(self, other):
        """ Returns true is self is a directory and other is a sub-element
        """
        if not self.is_directory:
            return False
        return other.path.startswith(self.path+"/")

    def is_effectively_equal_to(self, other):
        """ Compares two paths. Paths are considered
            effectively equals if their timestamps are
            within 10 microseconds
        """
        if type(other) is type(self):
            if(self.is_directory and other.is_directory and
               self.path == other.path):
                return True
            if(self.path == other.path and
               self.size == other.size and
               self.is_directory == other.is_directory and
               abs(self.time_stamp-other.time_stamp) < datetime.timedelta(microseconds=10)):
                return True
        return False

    @classmethod
    def from_json(cls, path_json, is_local=True):
        """ Builds a PathElement from a JSON rclone entry
        """
        path_name = path_json["Path"]
        path_is_dir = True if path_json["IsDir"] else False
        path_size = path_json["Size"]
        path_datetime = parse_rfc3339(path_json["ModTime"])
        return cls(path_name, path_datetime, path_size, path_is_dir, is_local)
