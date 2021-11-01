""" UpBack configuration singleton """

import json
import datetime

from .const import *

class ConfigurationOptions:
    """ Field names for Configuration
    """
    INIT_PULL = "init_pull"
    INIT_PUSH = "init_push"
    RESUME = "resume"
    FORCE = "force"
    RCLONE_PATH = "rclone_path"
    RCLONE_EXECUTABLE = "rclone_executable"
    INTERACTIVE = "interactive"
    VERBOSE = "verbose"
    VERBOSE_L2 = "verbose_l2"
    CONF_PATH = "conf_path"
    RCLONE_EXECUTABLE_DEFAULT = "rclone"
    REMOTE = "remote"
    REMOTE_BACKUP_DIR = "remote_backup_dir"
    REMOTE_BACKUP_SUFFIX = "remote_backup_suffix"
    OPT_INTERACTIVE = "i"
    OPT_VERBOSE = "v"
    OPT_VERBOSE_L2 = "vv"

class Configuration(ConfigurationOptions):
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
        self.nonpersistent_settings = [ # These are the settings that are not written to disk when calling write()
            self.INIT_PULL, self.INIT_PUSH, self.RESUME, self.FORCE, self.RCLONE_PATH, self.RCLONE_EXECUTABLE,
            self.INTERACTIVE, self.VERBOSE, self.VERBOSE_L2, self.CONF_PATH] 
        self.init_pull = self.INIT_PULL in arguments_map
        self.init_push = self.INIT_PUSH in arguments_map
        self.resume = self.RESUME in arguments_map
        self.force = self.FORCE in arguments_map
        if self.RCLONE_PATH in arguments_map and arguments_map[self.RCLONE_PATH]:
            self.rclone_path = arguments_map[self.RCLONE_PATH]
        else:
            self.rclone_path = ""
        if self.RCLONE_EXECUTABLE in arguments_map and arguments_map[self.RCLONE_EXECUTABLE]:
            self.rclone_executable = arguments_map[self.RCLONE_EXECUTABLE]
        else:
            self.rclone_executable = self.RCLONE_EXECUTABLE_DEFAULT
        if self.REMOTE in arguments_map and arguments_map[self.REMOTE]:
            self.remote = arguments_map[self.REMOTE]
        else:
            self.remote = None
        if self.REMOTE_BACKUP_DIR in arguments_map and arguments_map[self.REMOTE_BACKUP_DIR]:
            self.remote_backup = arguments_map[self.REMOTE_BACKUP_DIR]
        else:
            self.remote_backup = None
        if self.REMOTE_BACKUP_SUFFIX in arguments_map and arguments_map[self.REMOTE_BACKUP_SUFFIX]:
            self.backup_suffix = datetime.datetime.now().strftime(arguments_map[self.REMOTE_BACKUP_SUFFIX])
        else:
            self.backup_suffix = datetime.datetime.now().strftime(BACKUP_SUFFIX_DEFAULT)
        if self.OPT_INTERACTIVE in arguments_map and arguments_map[self.OPT_INTERACTIVE]:
            self.interactive = True
        else:
            self.interactive = False
        if self.OPT_VERBOSE in arguments_map and arguments_map[self.OPT_VERBOSE]:
            self.verbose = True
        else:
            self.verbose = False
        if self.OPT_VERBOSE_L2 in arguments_map and arguments_map[self.OPT_VERBOSE_L2]:
            self.verbose = True
            self.verbose_l2 = True
        else:
            self.verbose_l2 = False
        self.conf_path = ""
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
