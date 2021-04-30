""" UpBack configuration singleton """

import json
import datetime

from .const import *

class Configuration(object):
    """ Configuration class
        Fields are read from json file
    """
    def __new__(cls, *args, **kwds):
        singleton = cls.__dict__.get("__it__")
        if singleton is not None:
            return singleton
        cls.__it__ = singleton = object.__new__(cls)
        singleton.setup(*args, **kwds)
        return singleton

    def setup(self, arguments):
        """ Initialization method, called on singleton instantiation """
        arguments_map = vars(arguments)
        self.nonpersistent_settings = ["nonpersistent_settings"]
        self.init_pull = True if "init_pull" in arguments_map else False
        self.nonpersistent_settings.append("init_pull")
        self.init_push = True if "init_push" in arguments_map else False
        self.nonpersistent_settings.append("init_push")
        self.resume = True if "resume" in arguments_map else False
        self.nonpersistent_settings.append("resume")
        self.force = True if "force" in arguments_map else False
        self.nonpersistent_settings.append("force")
        if "rclone_path" in arguments_map and arguments_map["rclone_path"]:
            self.rclone_path = arguments_map["rclone_path"]
        else:
            self.rclone_path = ""
        self.nonpersistent_settings.append("rclone_path")
        if "rclone_executable" in arguments_map and arguments_map["rclone_executable"]:
            self.rclone_executable = arguments_map["rclone_executable"]
        else:
            self.rclone_executable = "rclone"
        self.nonpersistent_settings.append("rclone_executable")
        if "remote" in arguments_map and arguments_map["remote"]:
            self.remote = arguments_map["remote"]
        else:
            self.remote = None
        if "remote_backup_dir" in arguments_map and arguments_map["remote_backup_dir"]:
            self.remote_backup = arguments_map["remote_backup_dir"]
        else:
            self.remote_backup = None
        if "remote_backup_suffix" in arguments_map and arguments_map["remote_backup_suffix"]:
            self.backup_suffix = datetime.datetime.now().strftime(arguments_map["remote_backup_suffix"])
        else:
            self.backup_suffix = datetime.datetime.now().strftime(BACKUP_SUFFIX_DEFAULT)
        if "i" in arguments_map and arguments_map["i"]:
            self.interactive = True
        else:
            self.interactive = False
        self.nonpersistent_settings.append("interactive")
        if "v" in arguments_map and arguments_map["v"]:
            self.verbose = True
        else:
            self.verbose = False
        self.nonpersistent_settings.append("verbose")
        if "vv" in arguments_map and arguments_map["vv"]:
            self.verbose = True
            self.verbose_l2 = True
        else:
            self.verbose_l2 = False
        self.nonpersistent_settings.append("verbose_l2")
        self.conf_path = ""
        self.nonpersistent_settings.append("conf_path")
        self.no_backup = False
        self.global_excludes = []

    def read_file(self, conf_path):
        """ Read configuration elements from file
        """
        # pylint: disable=attribute-defined-outside-init
        with open(conf_path, "r") as conf_fp:
            self.conf_path = conf_path
            conf_json = json.load(conf_fp)
            if not "remote" in conf_json:
                raise IOError("Wrong configuration file format")
            self.remote = conf_json["remote"]
            self.no_backup = False
            if "no_backup" in conf_json and conf_json["no_backup"]:
                self.no_backup = True
            if "remote_backup" in conf_json:
                self.remote_backup = conf_json["remote_backup"]
            elif not self.no_backup:
                raise IOError("remote_backup missing")
            if "backup_suffix" in conf_json and conf_json["backup_suffix"]:
                self.backup_suffix = datetime.datetime.now().strftime(conf_json["backup_suffix"])
            else:
                self.backup_suffix = datetime.datetime.now().strftime(BACKUP_SUFFIX_DEFAULT)
            if "global_excludes" in conf_json and conf_json["global_excludes"]:
                self.global_excludes = conf_json["global_excludes"]
            else:
                self.global_excludes = []

    def write(self, path=None):
        """ Persists the configuration
        """
        path = self.conf_path if path is None else path
        with open(path, "w") as conf_fp:
            attributes = self.__dict__.copy()
            for nonpersistent_attribute in self.nonpersistent_settings:
                if nonpersistent_attribute in attributes:
                    del attributes[nonpersistent_attribute]
            json.dump(attributes, conf_fp, indent=4)
