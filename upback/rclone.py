""" Simple rclone interface """

import os
import logging
import json
import subprocess
import tempfile
import re

from .util import parse_rfc3339

class RClone(object):
    """ Wrapper class around the rclone executable """
    def __new__(cls, *args, **kwds):
        singleton = cls.__dict__.get("__it__")
        if singleton is not None:
            return singleton
        cls.__it__ = singleton = object.__new__(cls)
        singleton.setup(*args, **kwds)
        return singleton

    def setup(self, rclone_path="", rclone_executable="rclone"):
        """ Setup the rclone path and executable """
        if not rclone_path:
            self.rclone_file = rclone_executable
        else:
            self.rclone_file = os.path.join(rclone_path, rclone_executable)
        self.harmonize_timestamp_precision = True #TODO: set this depending on rclone version

    def backup_operation(self, args, no_backup=False, remote_backup=None, remote_suffix=None):
        """ Backup-aware operation """
        if not no_backup:
            if remote_backup:
                args += ["--backup-dir", remote_backup]
                if remote_suffix:
                    args += ["--suffix", remote_suffix]
        return self.run(args)

    def mkdir(self, path):
        """ mkdir """
        args = ["mkdir", path]
        return self.run(args)

    def delete(self, path, no_backup=False, remote_backup=None, remote_suffix=None):
        """ delete """
        args = ["delete", path]
        return self.backup_operation(args, no_backup, remote_backup, remote_suffix)

    def purge(self, path, no_backup=False, remote_backup=None, remote_suffix=None):
        """ purge: delete a path and its contents """
        args = ["purge", path]
        return self.backup_operation(args, no_backup, remote_backup, remote_suffix)

    def copy(self, source, dest, no_backup=False, remote_backup=None, remote_suffix=None):
        """ copy """
        args = ["copyto", source, dest]
        return self.backup_operation(args, no_backup, remote_backup, remote_suffix)

    def move(self, source, dest, no_backup=False, remote_backup=None, remote_suffix=None):
        """ move """
        args = ["moveto", source, dest]
        return self.backup_operation(args, no_backup, remote_backup, remote_suffix)

    def sync(self, source, dest, no_backup=False, remote_backup=None, remote_suffix=None):
        """ sync: make destination the same as source """
        args = ["sync", source, dest]
        return self.backup_operation(args, no_backup, remote_backup, remote_suffix)

    def lsjson(self, path):
        args = ["lsjson", "-R", "--skip-links", path]
        output = self.run(args)
        if self.harmonize_timestamp_precision:
            top_precision = 0
            paths_list = json.loads(output)
            for path_json in paths_list:
                datetime = path_json["ModTime"]
                (_, time_precision) = parse_rfc3339(datetime, report_precision=True)
                if time_precision > top_precision:
                    top_precision = time_precision
            #now make all timestamps use the same number of decimal digits
            #TODO: use it only with older version of rclone
            def replacer(matchobj):
                time = matchobj.group(1)
                decimal = matchobj.group(2)
                if not decimal:
                    decimal = "."
                return time+(decimal+("0"*top_precision))[0:top_precision+1]
            for path_json in paths_list:
                path_json["ModTime"] = re.sub(r'(\d\d?:\d\d?:\d\d?)(\.\d+)?', replacer, path_json["ModTime"])
            return json.dumps(paths_list)
        else:
            return output

    def write_file(self, path, content):
        """ Writes content to a file. Operates by creating a tempfile and moving
            it with rclone
        """
        tmp_fp, tmp_filename = tempfile.mkstemp()
        os.write(tmp_fp, bytes(content, encoding='UTF-8'))
        os.close(tmp_fp)
        self.move(tmp_filename, path)

    def run(self, args):
        """ Invoke rclone with the given arguments """
        args = [self.rclone_file] + args
        logging.info("Running "+str(args))
        output = subprocess.check_output(args, stderr=subprocess.STDOUT, encoding='UTF-8')
        logging.log(logging.INFO-1, "Output: "+output)
        return output
