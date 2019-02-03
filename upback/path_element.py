"""
PathElement class, use to represent path entries
"""

import datetime
import os
import logging

from .util import parse_rfc3339
from .const import * # pylint: disable=unused-wildcard-import

class PathElement(object):
    """ Path elements - we synchronize these
    """
    def __init__(self, path, time_stamp=0, time_precision=0, size=0, is_directory=False, is_local=True):
        self.init(path, time_stamp, time_precision, size, is_directory, is_local)

    def __eq__(self, other):
        if type(other) is type(self):
            return self.__dict__ == other.__dict__
        return False

    def init(self, path, time_stamp, time_precision, size, is_directory, is_local):
        """ Initialize a PathElement
        """
        self.path = path
        self.time_stamp = time_stamp
        self.time_precision = time_precision
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
            within 10 microseconds if both elements support 
            at least microseconds precision. 
            Otherwise if they are within 1 microsecond of 
            the precision of the least precise.
        """
        if type(other) is type(self):
            if(self.is_directory and other.is_directory and
               self.path == other.path):
                return True
            if(self.path == other.path and
               self.size == other.size and
               self.is_directory == other.is_directory):
                #compare time stamps taking precision into account
                if self.time_precision >= 6 and other.time_precision >= 6: #if at least microseconds precision -> effectively_equal if within 10 microseconds
                    return abs(self.time_stamp-other.time_stamp) < datetime.timedelta(microseconds=10)
                else: #precision is less than microseconds -> effectively_equal if equal within 1 microsecond of the precision of the least precise
                    min_precision = self.time_precision if self.time_precision < other.time_precision else other.time_precision
                    granularity = 10**(6-min_precision)-1
                    return abs(self.time_stamp-other.time_stamp) < datetime.timedelta(microseconds=granularity)
        return False

    @classmethod
    def from_json(cls, path_json, is_local=True):
        """ Builds a PathElement from a JSON rclone entry
        """
        path_name = path_json["Path"]
        path_is_dir = True if path_json["IsDir"] else False
        path_size = path_json["Size"]
        (path_datetime, path_time_precision) = parse_rfc3339(path_json["ModTime"], report_precision=True)
        return cls(path_name, path_datetime, path_time_precision, path_size, path_is_dir, is_local)
