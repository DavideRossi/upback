#!/usr/bin/python

""" UpBack unit tests """

import unittest
import os
import tempfile
import logging
import json
from .rclone import RClone
from .upback import (PathElement, upback)
from .configuration import Configuration
from .const import *

class UpbackTestCase(unittest.TestCase):
    """ Base test case class """

    @classmethod
    def setUpRemoteRoot(cls, remoteroot):
        """ Sets the remote to be used in the tests """
        cls.remoteroot = remoteroot

    @classmethod
    def setUpSubdir(cls, subdir):
        """ Sets the local subdir to run the tests from """
        cls.subdir = subdir

    @classmethod
    def setUpClass(cls):
        cls.rclone = RClone()
        cls.localroot = tempfile.mkdtemp(prefix="upback_local")
        cls.tmp = tempfile.mkdtemp(prefix="upback_tmp")
        try:
            cls.rclone.purge(cls.remoteroot)
        except:
            pass
        cls.rclone.mkdir(cls.remoteroot)

        cls.rclone.mkdir(cls.localroot+"/a")
        cls.rclone.mkdir(cls.localroot+"/a/b")
        cls.rclone.mkdir(cls.localroot+"/c")
        cls.rclone.mkdir(cls.localroot+"/a/d")
        cls.rclone.mkdir(cls.localroot+"/c/local2")
        cls.rclone.mkdir(cls.localroot+"/c/local2/a")
        cls.rclone.mkdir(cls.localroot+"/c/local2/a/b")
        cls.rclone.mkdir(cls.localroot+"/c/local2/a/d")
        cls.file_contents = {
            "a/a1.txt": "12",
            "a/a2.txt": "123",
            "a/b/b1.txt": "1234",
            "c/local2/a/a1.txt": "12",
            "c/local2/a/a2.txt": "123",
            "c/local2/a/b/b1.txt": "1234"
        }
        cls.local = cls.localroot
        for path in cls.file_contents:
            cls.write_file_local(path)
        cls.path_contents = {
            "a": PathElement("a", is_directory=True),
            "a/b": PathElement("a/b", is_directory=True),
            "c": PathElement("c", is_directory=True),
            "a/d": PathElement("a/d", is_directory=True),
            "c/local2": PathElement("c/local2", is_directory=True),
            "c/local2/a": PathElement("c/local2/a", is_directory=True),
            "c/local2/a/b": PathElement("c/local2/a/b", is_directory=True),
            "c/local2/a/d": PathElement("c/local2/a/d", is_directory=True),
            "a/a1.txt": PathElement("a/a1.txt", is_directory=False, size=len(cls.file_contents["a/a1.txt"])),
            "a/a2.txt": PathElement("a/a2.txt", is_directory=False, size=len(cls.file_contents["a/a2.txt"])),
            "a/b/b1.txt": PathElement("a/b/b1.txt", is_directory=False, size=len(cls.file_contents["a/b/b1.txt"])),
            "c/local2/a/a1.txt": PathElement("c/local2/a/a1.txt", is_directory=False, size=len(cls.file_contents["c/local2/a/a1.txt"])),
            "c/local2/a/a2.txt": PathElement("c/local2/a/a2.txt", is_directory=False, size=len(cls.file_contents["c/local2/a/a2.txt"])),
            "c/local2/a/b/b1.txt": PathElement("c/local2/a/b/b1.txt", is_directory=False, size=len(cls.file_contents["c/local2/a/b/b1.txt"])),
            UPBACK_CONF_FILE: PathElement(UPBACK_CONF_FILE, is_directory=False, size=-1)
        }

        if cls.subdir is not None:
            cls.local = cls.localroot+"/"+cls.subdir
            cls.remote = cls.remoteroot+"/"+cls.subdir
        else:
            cls.local = cls.localroot
            cls.remote = cls.remoteroot

        #run upback as if it was run from command line with init-push
        if cls.configuration is None:
            args = lambda: None
            args.init_push = True
            args.remote = cls.remoteroot
            cls.configuration = Configuration(args)
        else:
            cls.configuration.init_push = True
            cls.configuration.remote = cls.remoteroot
        cls.run_upback_from(cls.localroot)
        #restore configuration to a normal state
        cls.configuration.init_push = None
        cls.configuration.init_pull = None
        #we need this because of rclone bug #1837
        #cls.rclone.mkdir(cls.remoteroot+"/a/d")
        #cls.rclone.mkdir(cls.remoteroot+"/c/local2/a/d")
        cls.run_upback_from(cls.localroot)
        #relativize path contents wrt subdir
        if cls.subdir is not None:
            new_path_contents = {}
            for path, path_element in cls.path_contents.iteritems():
                if path.startswith(cls.subdir+"/"):
                    path = path[len(cls.subdir+"/"):]
                    path_element.path = path
                    new_path_contents[path] = path_element
            cls.path_contents = new_path_contents

    @classmethod
    def tearDownClass(cls):
        cls.rclone.purge(cls.localroot)
        cls.rclone.purge(cls.tmp)
        cls.rclone.purge(cls.remoteroot)

    @classmethod
    def write_file_local(cls, path):
        """ write/create file in local path """
        cls.rclone.write_file(cls.local+"/"+path, cls.file_contents[path])

    @classmethod
    def write_file_remote(cls, path):
        """ write/create file in remote path """
        cls.rclone.write_file(cls.remoteroot+"/"+path, cls.file_contents[path])

    @classmethod
    def write_file_local_and_remote(cls, path):
        cls.write_file_local(path)
        cls.rclone.copy(cls.local+"/"+path, cls.remoteroot+"/"+path)

    def paths_elements_are_matching(self, path_element1, path_element2):
        """ Tests if path elements are matching.
            For testing purposes we limit to type, path and size
        """
        if(path_element1.is_directory and path_element2.is_directory and
           path_element1.path == path_element2.path):
            return True
        if(path_element1.path == path_element2.path and
           (path_element1.size == path_element2.size or path_element1.size == -1 or path_element2.size == -1) and
           path_element1.is_directory == path_element2.is_directory):
            return True
        return False

    def path_contains(self, path, path_elements):
        """ Checks if a path contains the specified elements """
        args = ["lsjson", "-R", path]
        output = self.rclone.run(args)
        paths_list = json.loads(output)
        paths = {}
        for path in paths_list:
            if path["Name"] != UPBACK_REMOTE_BACKUP:
                path_entry = PathElement.from_json(path)
                paths[path_entry.path] = path_entry
        if len(paths) != len(path_elements):
            logging.warn("size differs")
            return False
        for path, path_element in path_elements:
            if not path in paths:
                logging.warn("path "+path+" not found")
                return False
            other_path_element = paths[path]
            if not self.paths_elements_are_matching(path_element, other_path_element):
                logging.warn("path "+path+" not equal")
                return False
        return True

    @classmethod
    def run_upback_from(cls, path):
        """ Run UpBack from a path then restore previous cwd """
        cwd = os.getcwd()
        os.chdir(path)
        upback()
        os.chdir(cwd)

    # test methods 

    def test_new_local_file(self):
        """ new local file """
        self.rclone.write_file(self.local+"/a/a3.txt", "123")
        self.run_upback_from(self.local)
        self.path_contents["a/a3.txt"] = PathElement("a/a3.txt", size=3)
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        del self.path_contents["a/a3.txt"]
        self.rclone.delete(self.local+"/a/a3.txt")
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_update_local(self):
        """ update local """
        self.rclone.write_file(self.local+"/a/a1.txt", "123456")
        self.run_upback_from(self.local)
        self.path_contents["a/a1.txt"].size = 6
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.write_file_local_and_remote("a/a1.txt")
        self.path_contents["a/a1.txt"].size = len(self.file_contents["a/a1.txt"])
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_update_remote(self):
        """ update remote """
        self.rclone.copy(self.local+"/a/a1.txt", self.remote+"/a/a2.txt")
        self.run_upback_from(self.local)
        self.path_contents["a/a2.txt"].size = self.path_contents["a/a1.txt"].size
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.write_file_local_and_remote("a/a2.txt")
        self.path_contents["a/a2.txt"].size = len(self.file_contents["a/a2.txt"])
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_update_both_sides(self):
        """ update both sides """
        self.rclone.write_file(self.local+"/a/a1.txt", "1234567")
        self.rclone.write_file(self.remote+"/a/a2.txt", "12345678")
        self.run_upback_from(self.local)
        self.path_contents["a/a1.txt"].size = 7
        self.path_contents["a/a2.txt"].size = 8
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.write_file_local_and_remote("a/a1.txt")
        self.write_file_local_and_remote("a/a2.txt")
        self.path_contents["a/a1.txt"].size = len(self.file_contents["a/a1.txt"])
        self.path_contents["a/a2.txt"].size = len(self.file_contents["a/a2.txt"])
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_delete_local(self):
        """ delete local """
        # delete
        self.rclone.delete(self.local+"/a/a1.txt")
        self.run_upback_from(self.local)
        path_element = self.path_contents["a/a1.txt"]
        del self.path_contents["a/a1.txt"]
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        # restore (from tmp)
        self.write_file_local_and_remote("a/a1.txt")
        self.path_contents["a/a1.txt"] = path_element
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_delete_remote(self):
        """ delete remote """
        #delete
        self.rclone.delete(self.remote+"/a/a2.txt")
        self.run_upback_from(self.local)
        path_element = self.path_contents["a/a2.txt"]
        del self.path_contents["a/a2.txt"]
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.write_file_local_and_remote("a/a2.txt")
        self.path_contents["a/a2.txt"] = path_element
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_delete_both(self):
        """ delete both """
        #delete
        self.rclone.delete(self.local+"/a/a1.txt")
        self.rclone.delete(self.remote+"/a/a2.txt")
        self.run_upback_from(self.local)
        path_element_a1 = self.path_contents["a/a1.txt"]
        path_element_a2 = self.path_contents["a/a2.txt"]
        del self.path_contents["a/a1.txt"]
        del self.path_contents["a/a2.txt"]
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.write_file_local_and_remote("a/a1.txt")
        self.write_file_local_and_remote("a/a2.txt")
        self.path_contents["a/a1.txt"] = path_element_a1
        self.path_contents["a/a2.txt"] = path_element_a2
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_update_conflict_resolution_local(self):
        """ update both with conflict and resolution as local """
        # conflict
        self.rclone.write_file(self.local+"/a/a1.txt", "123")
        self.rclone.write_file(self.remote+"/a/a1.txt", "1234")
        self.run_upback_from(self.local)
        #load and modify upback.UPBACK_CONFLICTS_FILE
        with open(self.local+os.sep+UPBACK_CONFLICTS_FILE, "r+") as conflicts_fp:
            json_conflits = json.load(conflicts_fp)
            json_conflits[0]["resolution"] = "L"
            conflicts_fp.seek(0)
            json.dump(json_conflits, conflicts_fp)
            conflicts_fp.truncate()
        #run upback in resume mode
        self.configuration.resume = True
        self.run_upback_from(self.local)
        self.configuration.resume = False
        self.path_contents["a/a1.txt"].size = 3
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.write_file_local_and_remote("a/a1.txt")
        self.path_contents["a/a1.txt"].size = len(self.file_contents["a/a1.txt"])
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_update_conflict_resolution_remote(self):
        """ update both with conflict and resolution as remote """
        # conflict
        self.rclone.write_file(self.local+"/a/a1.txt", "123")
        self.rclone.write_file(self.remote+"/a/a1.txt", "1234")
        self.run_upback_from(self.local)
        #load and modify upback.UPBACK_CONFLICTS_FILE
        with open(self.local+os.sep+UPBACK_CONFLICTS_FILE, "r+") as conflicts_fp:
            json_conflits = json.load(conflicts_fp)
            json_conflits[0]["resolution"] = "R"
            conflicts_fp.seek(0)
            json.dump(json_conflits, conflicts_fp)
            conflicts_fp.truncate()
        #run upback in resume mode
        self.configuration.resume = True
        self.run_upback_from(self.local)
        self.configuration.resume = False
        self.path_contents["a/a1.txt"].size = 4
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.write_file_local_and_remote("a/a1.txt")
        self.path_contents["a/a1.txt"].size = len(self.file_contents["a/a1.txt"])
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_update_conflict_resolution_delete(self):
        """ update both with conflict and resolution as delete """
        # conflict
        self.rclone.write_file(self.local+"/a/a1.txt", "123")
        self.rclone.write_file(self.remote+"/a/a1.txt", "1234")
        self.run_upback_from(self.local)
        #load and modify upback.UPBACK_CONFLICTS_FILE
        with open(self.local+os.sep+UPBACK_CONFLICTS_FILE, "r+") as conflicts_fp:
            json_conflits = json.load(conflicts_fp)
            json_conflits[0]["resolution"] = "X"
            conflicts_fp.seek(0)
            json.dump(json_conflits, conflicts_fp)
            conflicts_fp.truncate()
        #run upback in resume mode
        self.configuration.resume = True
        self.run_upback_from(self.local)
        self.configuration.resume = False
        path_element = self.path_contents["a/a1.txt"]
        del self.path_contents["a/a1.txt"]
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.write_file_local_and_remote("a/a1.txt")
        self.path_contents["a/a1.txt"] = path_element
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_update_conflict_resolution_ignore(self):
        """ update both with conflict and resolution as ignore """
        # conflict
        self.rclone.write_file(self.local+"/a/a1.txt", "123")
        self.rclone.write_file(self.remote+"/a/a1.txt", "1234")
        self.run_upback_from(self.local)
        #load and modify upback.UPBACK_CONFLICTS_FILE
        with open(self.local+os.sep+UPBACK_CONFLICTS_FILE, "r+") as conflicts_fp:
            json_conflits = json.load(conflicts_fp)
            json_conflits[0]["resolution"] = "I"
            conflicts_fp.seek(0)
            json.dump(json_conflits, conflicts_fp)
            conflicts_fp.truncate()
        #run upback in resume mode
        self.configuration.resume = True
        self.run_upback_from(self.local)
        self.configuration.resume = False
        self.path_contents["a/a1.txt"].size = 3
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        self.path_contents["a/a1.txt"].size = 4
        contents = self.path_contents.items()
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.write_file_local_and_remote("a/a1.txt")
        self.path_contents["a/a1.txt"].size = len(self.file_contents["a/a1.txt"])
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_delete_nonempty_dir_local(self):
        """ delete non-empty local dir """
        self.rclone.purge(self.local+"/a/b")
        self.run_upback_from(self.local)
        path_element_b = self.path_contents["a/b"]
        path_element_b1_txt = self.path_contents["a/b/b1.txt"]
        del self.path_contents["a/b"]
        del self.path_contents["a/b/b1.txt"]
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.rclone.mkdir(self.local+"/a/b")
        self.rclone.mkdir(self.remote+"/a/b")
        self.write_file_local_and_remote("a/b/b1.txt")
        self.path_contents["a/b"] = path_element_b
        self.path_contents["a/b/b1.txt"] = path_element_b1_txt
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_delete_empty_dir_local(self):
        """ delete empty local dir """
        self.rclone.purge(self.local+"/a/d")
        self.run_upback_from(self.local)
        path_element = self.path_contents["a/d"]
        del self.path_contents["a/d"]
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.rclone.mkdir(self.local+"/a/d")
        self.rclone.mkdir(self.remote+"/a/d")
        self.path_contents["a/d"] = path_element
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_delete_nonempty_dir_remote(self):
        """ delete non-empty remote dir """
        self.rclone.purge(self.remote+"/a/b")
        self.run_upback_from(self.local)
        path_element_b = self.path_contents["a/b"]
        path_element_b1_txt = self.path_contents["a/b/b1.txt"]
        del self.path_contents["a/b"]
        del self.path_contents["a/b/b1.txt"]
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.rclone.mkdir(self.local+"/a/b")
        self.rclone.mkdir(self.remote+"/a/b")
        self.write_file_local_and_remote("a/b/b1.txt")
        self.path_contents["a/b"] = path_element_b
        self.path_contents["a/b/b1.txt"] = path_element_b1_txt
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_delete_empty_dir_remote(self):
        """ delete empty local dir """
        self.rclone.purge(self.remote+"/a/d")
        self.run_upback_from(self.local)
        path_element = self.path_contents["a/d"]
        del self.path_contents["a/d"]
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.rclone.mkdir(self.local+"/a/d")
        self.rclone.mkdir(self.remote+"/a/d")
        self.path_contents["a/d"] = path_element
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_exclude_update_local(self):
        """ update local with exclusion """
        if self.subdir is not None:
            self.skipTest("Cannot run from inner directory")
        self.rclone.write_file(self.local+"/a/a1.txt", "123456")
        self.rclone.write_file(self.local+"/a/b/b1.txt", "123456")
        self.configuration.global_excludes = ["a?.txt", "a/b/*"]
        self.configuration.write()
        self.run_upback_from(self.local)
        self.path_contents["a/a1.txt"].size = 6
        self.path_contents["a/b/b1.txt"].size = 6
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        self.path_contents["a/a1.txt"].size = len(self.file_contents["a/a1.txt"])
        self.path_contents["a/b/b1.txt"].size = len(self.file_contents["a/b/b1.txt"])
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.write_file_local("a/a1.txt")
        self.write_file_local("a/b/b1.txt")
        self.configuration.global_excludes = []
        self.configuration.write()
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_update_local_above_working_dir(self):
        """ update local above working directory """
        if self.subdir is not None:
            self.skipTest("Cannot run from inner directory")
        self.rclone.write_file(self.local+"/a/a1.txt", "123456")
        self.run_upback_from(self.local+"/c/local2")
        self.path_contents["a/a1.txt"].size = 6
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        self.path_contents["a/a1.txt"].size = len(self.file_contents["a/a1.txt"])
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.write_file_local("a/a1.txt")
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

    def test_update_remote_above_working_dir(self):
        """ update remote above working directory """
        if self.subdir is not None:
            self.skipTest("Cannot run from inner directory")
        self.rclone.write_file(self.remote+"/a/a1.txt", "123456")
        self.run_upback_from(self.local+"/c/local2")
        contents = self.path_contents.items()
        local_matches = self.path_contains(self.local, contents)
        self.path_contents["a/a1.txt"].size = 6
        remote_matches = self.path_contains(self.remote, contents)
        #restore
        self.path_contents["a/a1.txt"].size = len(self.file_contents["a/a1.txt"])
        self.write_file_local("a/a1.txt")
        self.run_upback_from(self.local)
        #assert
        self.assertTrue(local_matches)
        self.assertTrue(remote_matches)

# thanks Python for this awesome class attribute initialization!
UpbackTestCase.remote = None
UpbackTestCase.subdir = None
UpbackTestCase.configuration = None

if __name__ == '__main__':
    logging.basicConfig(level=logging.WARN)
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(UpbackTestCase)
    UpbackTestCase.setUpRemoteRoot(tempfile.mkdtemp(prefix="upback_remote"))
    unittest.TextTestRunner(verbosity=2).run(suite)
    UpbackTestCase.setUpSubdir("c/local2")
    unittest.TextTestRunner(verbosity=2).run(suite)
#    UpbackTestCase.setUpRemoteRoot("gdrive:Back")
#    UpbackTestCase.setUpSubdir(None)
#    unittest.TextTestRunner(verbosity=2).run(suite)
#    UpbackTestCase.setUpSubdir("c/local2")
#    unittest.TextTestRunner(verbosity=2).run(suite)
