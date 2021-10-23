#!/usr/bin/python
"""
UpBack: synchronize (both ways) two filesystem branches using
rclone, so that you can sync local and remote file systems
on Amazon Cloud Drive, Google Drive, Dropbox, etc...
"""

import os
import json
import logging
import collections
import fnmatch

from .rclone import RClone
from .configuration import Configuration
from .path_element import PathElement
from .operations import Operations
from .util import lock_file, remove_lock_file, is_path_local, wildcard_match
from .const import * # pylint: disable=unused-wildcard-import

class UpBackException(Exception):
    """ Application exception """
    pass

def rclone_ls(path):
    """ Returns a dictionary of paths
        as retrieved by rclone lsjson
        Pathnames are the keys of the dictionary,
        each entry is another dictionary with
        path details
    """
    is_local = is_path_local(path)
    rclone = RClone()
    output = rclone.lsjson(path)
    paths_list = json.loads(output)
    paths = {}
    for path in paths_list:
        path_entry = PathElement.from_json(path)
        path_entry.is_local = is_local
        paths[path_entry.path] = path_entry
    return paths

#TODO use some kind of caching
def exclude(directory_path):
    """ Returns a list of paths included in an
        upback exclude file.
    """
    lines = []
    #TODO was lines = [UPBACK_EXCLUDE_FILE, UPBACK_CONF_FILE]
    exclude_path = os.path.join(directory_path, UPBACK_EXCLUDE_FILE)
    if os.path.exists(exclude_path):
        with open(exclude_path, "r") as exclude_fp:
            lines += exclude_fp.read().splitlines()
    return lines

def exclude_filter(directory_path, path, basename=None):
    """ Starting from directory_path evaluates all
        local excludes to see if path is to be filtered.
        path is assumed to be a relative path into directory_path.
        A path/name is filtered if name is excluded in path/UPBACK_EXCLUDE_FILE
        or if path is excluded from .. (and recursively up).
        An actual file/dir at path is not required to exist.
    """
    if not is_path_local(directory_path):
        return False
    if path == "":
        return False
    (head, tail) = os.path.split(path)
    if basename is None:
        basename = tail #we store this to later support subdir wildcards like **/match
    local_excludes = exclude(os.path.join(directory_path, head))
    for local_exclude in local_excludes:
        if wildcard_match(tail, local_exclude):
            return True
    return exclude_filter(directory_path, head, basename)

def filter_exclude_paths(base_path, paths):
    """ Apply exclude_filter to a set of paths relative
        to a base_path
    """
    retval = dict()
    for path in paths.keys():
        if not exclude_filter(base_path, path):
            retval[path] = paths[path]
    return retval

def find_backup_branch(path="", climb=True):
    """ Climbs the directory structure looking for a directory
        containing an upback configuration file.
        Returns the path to that configuration file
        if any, None otherwise.
        None is also returned if climbing back the hierarchy
        it finds that the current branch is excluded by
        the parent
    """
    if path == "":
        path = os.getcwd()
    path = os.path.realpath(path)
    current_dir_name = os.path.basename(os.path.normpath(path))
    logging.info("looking for backup configuration file in "+path+
                 " current dir name: "+current_dir_name)
    entries = os.listdir(path)
    conf_path = os.path.join(path, UPBACK_CONF_FILE)
    if UPBACK_CONF_FILE in entries and os.path.isfile(conf_path):
        # upback conf file found in current path
        return conf_path
    elif climb:
        # try upstream
        upper_path = os.path.realpath(os.path.join(path, os.pardir))
        if current_dir_name in exclude(upper_path):
            # we are excluded by the upper directory
            return None
        else:
            if path != upper_path:
                # we are not at root
                return find_backup_branch(os.path.realpath(upper_path))
            else:
                # root reached
                return None
    else:
        return None

def compute_operations(paths_all, paths_a, paths_b_backup, paths_b):
    """ Returns a dictionary of operations to perform
        to synchronize a and b.
        Keys are:
            - copy_a_to_b
            - copy_b_to_a
            - delete_from_a
            - delete_from_b
            - conflict
    """
    operations = Operations()
    for path in paths_all:
        if not path in paths_a and not path in paths_b_backup:
            a_op = CHANGE_NONE
        elif not path in paths_a and path in paths_b_backup:
            a_op = CHANGE_DELETED
        elif path in paths_a and not path in paths_b_backup:
            a_op = CHANGE_NEW
        elif (path in paths_a and path in paths_b_backup
              and paths_a[path].is_effectively_equal_to(paths_b_backup[path])):
            a_op = CHANGE_SAME
        elif (path in paths_a and path in paths_b_backup
              and not paths_a[path].is_effectively_equal_to(paths_b_backup[path])):
            a_op = CHANGE_UPDATED
        else: #path is newer in b_backup
            raise Exception()
        if not path in paths_b_backup and not path in paths_b:
            b_op = CHANGE_NONE
        elif not path in paths_b and path in paths_b_backup:
            b_op = CHANGE_DELETED
        elif path in paths_b and not path in paths_b_backup:
            b_op = CHANGE_NEW
        elif (path in paths_b_backup and path in paths_b
              and paths_b_backup[path].is_effectively_equal_to(paths_b[path])):
            b_op = CHANGE_SAME
        elif (path in paths_b_backup and path in paths_b
              and not paths_b_backup[path].is_effectively_equal_to(paths_b[path])):
            b_op = CHANGE_UPDATED
        else:
            raise Exception()
        if(path in paths_a and path in paths_b and
           paths_a[path].is_directory != paths_b[path].is_directory):
            operations.add_conflict(path, "is a file on one side and a directory in the other")
        elif a_op == CHANGE_NEW and b_op == CHANGE_NEW:
            if paths_a[path].is_effectively_equal_to(paths_b[path]):
                #same file and local and remote: backup is out of sync?
                pass
            else:
                #CONFLICT	created independently on both remotes
                operations.add_conflict(path, "has been changed in both local and remote")
        elif a_op == CHANGE_NEW and b_op == CHANGE_NONE:
            #COPY TO B
            operations.add_copy_a_to_b(path, False)
        elif a_op == CHANGE_DELETED and b_op == CHANGE_DELETED:
            #NOOP	deleted independently on both remotes, BB will be updated accordingly
            pass
        elif a_op == CHANGE_DELETED and b_op == CHANGE_SAME:
            #*DELETE B*	deleted in A
            operations.add_delete_from_b(path)
        elif a_op == CHANGE_DELETED and b_op == CHANGE_UPDATED:
            #CONFLICT	deleted in A, updated in B
            operations.add_conflict(path, "has been deleted in local and updated in remote")
        elif a_op == CHANGE_SAME and b_op == CHANGE_DELETED:
            #*DELETE A*	deleted in B
            operations.add_delete_from_a(path)
        elif a_op == CHANGE_SAME and b_op == CHANGE_SAME:
            #NOOP
            pass
        elif a_op == CHANGE_SAME and b_op == CHANGE_UPDATED:
            #*COPY TO A*	overwrite
            operations.add_copy_b_to_a(path, True)
        elif a_op == CHANGE_UPDATED and b_op == CHANGE_DELETED:
            #CONFLICT	updated in A and deleted in B
            operations.add_conflict(path, "has been changed in local and delete in remote")
        elif a_op == CHANGE_UPDATED and b_op == CHANGE_SAME:
            #*COPY TO B*	overwrite
            operations.add_copy_a_to_b(path, True)
        elif a_op == CHANGE_UPDATED and b_op == CHANGE_UPDATED:
            if paths_a[path].is_effectively_equal_to(paths_b[path]):
                #same file and local and remote: backup is out of sync?
                pass
            else:
                #CONFLICT	updated independently in A and B
                operations.add_conflict(path, "has been changed in both local and remote")
        elif a_op == CHANGE_NONE and b_op == CHANGE_NEW:
            #COPY TO A
            operations.add_copy_b_to_a(path)
        else:
            raise UpBackException("Unsupported synchronization case")
    return operations

def cleanup():
    """ Performs cleanup before program termination
    """
    remove_lock_file()

def save_backup(backup_path, remote):
    """ Saves a backup by storing the result of rclone lsjson into the backup file
    """
    try:
        rclone = RClone()
        output = rclone.lsjson(remote)
        json.loads(output) #raises ValueError if not json
        with open(os.path.join(backup_path, UPBACK_REMOTE_BACKUP), "w") as backup_fp:
            backup_fp.write(output)
    except ValueError:
        print(output)
        raise UpBackException("Invalid backup file format")

def retrieve_backup(backup_path, rel_path):
    """ Retrieves the backup for remote
        filtering out upper paths.
    """
    try:
        with open(os.path.join(backup_path, UPBACK_REMOTE_BACKUP), "r") as backup_fp:
            paths_json = json.load(backup_fp)
            paths = {}
            for path in paths_json:
                path_entry = PathElement.from_json(path)
                prefix = rel_path
                if prefix != "":
                    prefix += "/"
                if path_entry.path != prefix and path_entry.path.startswith(prefix):
                    new_path = path_entry.path[len(prefix):]
                    path_entry.path = new_path
                    paths[path_entry.path] = path_entry
            return paths
    except IOError:
        return None

def compact_deletes(delete_ops, path_elements):
    """ Compacts delete operations so that if a directory is to be deleted
        deletion of contained elements is ignored
    """
    dir_elements = []
    for del_op in delete_ops:
        path, _ = del_op
        path_element = path_elements[path]
        if path_element.is_directory:
            dir_elements.append(path_element)
    paths_to_ignore = []
    for del_op in delete_ops:
        path, _ = del_op
        path_element = path_elements[path]
        for dir_element in dir_elements:
            if dir_element.contains(path_element):
                paths_to_ignore.append(path)
    compacted_ops = []
    for del_op in delete_ops:
        path, _ = del_op
        if not path in paths_to_ignore:
            compacted_ops.append(del_op)
    return compacted_ops

def perform_operations(operations, paths_a, paths_b, remote, rel_path, no_backup, remote_backup=None, backup_suffix=None):
    """ Performs the operations as computed
    """
    rclone = RClone()
    for copy_op in operations.copy_a_to_b:
        path, backup = copy_op
        remote_path = rebase(rebase(path, rel_path), remote)
        if paths_a[path].is_directory:
            rclone.mkdir(remote_path)
        else:
            rclone.copy(path, remote_path, backup and not no_backup, remote_backup, backup_suffix)
    for copy_op in operations.copy_b_to_a:
        path, backup = copy_op
        remote_path = rebase(rebase(path, rel_path), remote)
        if paths_b[path].is_directory:
            rclone.mkdir(path)
        else:
            rclone.copy(remote_path, path)
    deletes = compact_deletes(operations.delete_from_a, paths_a)
    for del_op in deletes:
        path, _ = del_op
        if paths_a[path].is_directory:
            rclone.purge(path)
        else:
            rclone.delete(path)
    deletes = compact_deletes(operations.delete_from_b, paths_b)
    for del_op in deletes:
        path, backup = del_op
        remote_path = rebase(rebase(path, rel_path), remote)
        if paths_b[path].is_directory:
            rclone.purge(remote_path, backup and not no_backup, remote_backup, backup_suffix)
        else:
            rclone.delete(remote_path, backup and not no_backup, remote_backup, backup_suffix)

def merge_and_exclude_paths(paths_a, paths_b, rel_path, local_excludes, global_excludes):
    """ Returns a set with the union of all the paths contained
        in the first two arguments, intersected with the
        third argument
    """
    paths_all = set()
    for path in paths_a:
        paths_all.add(path)
    for path in paths_b:
        paths_all.add(path)
    for path_to_exclude in local_excludes:
        if path_to_exclude.startswith("./"):
            path_to_exclude = path_to_exclude[2:]
        if path_to_exclude in paths_all:
            paths_all.remove(path_to_exclude)
    for global_path_to_exclude in global_excludes + [UPBACK_CONF_FILE+".lock", UPBACK_REMOTE_BACKUP]:
        if "/" in global_path_to_exclude and rel_path is not None and rel_path != "" and rel_path != ".":
            path_to_exclude = os.path.relpath(global_path_to_exclude, rel_path)
        else:
            path_to_exclude = global_path_to_exclude
        to_exclude = set()
        for path in paths_all:
            if "/" in path_to_exclude:
                if fnmatch.fnmatch(path, path_to_exclude):
                    to_exclude.add(path)
            else:
                if fnmatch.fnmatch(os.path.basename(path), path_to_exclude):
                    to_exclude.add(path)
        if to_exclude:
            paths_all = paths_all - to_exclude
    return paths_all

def write_conflicts(conflicts, paths_a, paths_b):
    """ Writes conflicts to a json file
        The user can edit the file and resume sync with --resume
    """
    conflicts_json = []
    with open(UPBACK_CONFLICTS_FILE, "w") as conflicts_fp:
        for conflict in conflicts:
            (conflict_path, conflict_explaination) = conflict
            path_element_a = PathElement("", None, -1) if not conflict_path in paths_a else paths_a[conflict_path]
            path_element_b = PathElement("", None, -1) if not conflict_path in paths_b else paths_b[conflict_path]
            entries = collections.OrderedDict([
                ("path", conflict_path),
                ("local_size", path_element_a.size),
                ("local_datetime", str(path_element_a.time_stamp)),
                ("remote_size", path_element_b.size),
                ("remote_datetime", str(path_element_b.time_stamp)),
                ("resolution", "LRIX"),
                ("legenda", "L: local overwrites remote; R: remote overwrites local; "
                            "X: both local and remote are deleted; "
                            "I: Ignore this path "
                            "(will possibly generate a new conflict on subsequent runs)"),
                ("explaination", conflict_explaination)
            ])
            conflicts_json.append(entries)
        json.dump(conflicts_json, conflicts_fp, indent=4)

def init_push():
    """ Initialize an UpBack branch by synchronizing
        local -> remote
    """
    backup_config = find_backup_branch(climb=False)
    configuration = Configuration()
    if backup_config and configuration.remote:
        raise UpBackException("An UpBack configuration file is present, "
                              "remote argument cannot be used")
    elif not backup_config:
        configuration.write(UPBACK_CONF_FILE)
    else:
        configuration.read_file(backup_config)
    #sync local -> remote
    if not configuration.force:
        if rclone_ls(configuration.remote):
            raise UpBackException("Remote is not empty. To force initialization use --force")
    args = ["sync", ".", configuration.remote]
    if(not configuration.no_backup and
       configuration.remote_backup is not None and configuration.remote_backup != ""):
        args += ["--backup-dir", configuration.remote_backup,
                 "--suffix", configuration.backup_suffix]
    rclone = RClone()
    rclone.run(args)
    save_backup(".", configuration.remote)

def init_pull():
    """ Initialize an UpBack branch by synchronizing
        remote -> local
    """
    backup_config = find_backup_branch(climb=False)
    configuration = Configuration()
    local_is_empty = len(rclone_ls(".")) == 0
    if backup_config and configuration.remote:
        raise UpBackException("The current directory is already the root of "
                              "an existing UpBack backup")
    elif not backup_config:
        if not local_is_empty and not configuration.force:
            raise UpBackException("Local is not empty. To force initialization use --force")
        else:
            configuration.write(UPBACK_CONF_FILE)
    else: #TODO: part of an existing UpBack backup branch but no remote - does it make sense?
        configuration.read_file(backup_config)
    #sync remote -> local
    args = ["sync", "--create-empty-src-dirs", configuration.remote, "."]
    rclone = RClone()
    rclone.run(args)
    save_backup(".", configuration.remote)

def rebase(path_to_rebase, base):
    """ Rebase the parameter (a list or a single string)
    """
    if base is None or base == "" or base == ".":
        return path_to_rebase
    path_list = path_to_rebase if isinstance(path_to_rebase, list) else [path_to_rebase]
    rebased_paths = []
    for path in path_list:
        rebased_paths.append(os.path.join(base, path))
    return rebased_paths if isinstance(path_to_rebase, list) else rebased_paths[0]

def fix_conflicts(remote, local, remote_rel_path, remote_backup=None, backup_suffix=None):
    """ Fixes conflicts as per the conflicts file
        Returns a list of paths to ignore
    """
    try:
        ignore_paths = []
        remote_path = rebase(remote_rel_path, remote)
        rclone = RClone()
        with open(UPBACK_CONFLICTS_FILE, "r") as conflicts_fp:
            conflicts_json = json.load(conflicts_fp)
            for conflict_json in conflicts_json:
                resolution = conflict_json["resolution"]
                path = conflict_json["path"]
                if resolution == "L":
                    #copy local to remote
                    rclone.copy(path, rebase(path, remote_path), remote_backup=remote_backup,
                                remote_suffix=backup_suffix)
                elif resolution == "R":
                    #copy remote to local
                    rclone.copy(rebase(path, remote_path), path)
                elif resolution == "X":
                    #remove both local and remote
                    rclone.delete(path)
                    rclone.delete(rebase(path, remote_path), remote_backup=remote_backup,
                                  remote_suffix=backup_suffix)
                elif resolution == "I":
                    ignore_paths.append(conflict_json["path"])
                else:
                    raise UpBackException("Invalid resolution found")
        os.remove(UPBACK_CONFLICTS_FILE)
        return ignore_paths
    except IOError:
        raise UpBackException("Conflicts file not found or unreadable.")

def upback():
    """ Program entry point
    """
    try:
        configuration = Configuration()
        #initialize the RClone singleton
        RClone(configuration.rclone_path, configuration.rclone_executable)
        if configuration.init_pull:
            init_pull()
            return
        if configuration.init_push:
            init_push()
            return
        #look for conf file
        backup_config = find_backup_branch()
        if backup_config is None:
            raise UpBackException("The current directory does not belong to an UpBack backup")
        backup_config_path = os.path.dirname(backup_config)
        #lock conf file
        if not lock_file(backup_config+".lock"):
            raise UpBackException("Another instance of UpBack is running on this filesystem branch")
        #read conf file
        configuration.read_file(backup_config)
        #path from conf file dir to .
        rel_path = os.path.relpath(os.getcwd(), os.path.dirname(backup_config))
        if rel_path == ".":
            rel_path = ""
        #fix conflicts
        exclude_paths = []
        if configuration.resume:
            exclude_paths = fix_conflicts(configuration.remote, os.getcwd(), rel_path,
                                          configuration.remote_backup, configuration.backup_suffix)
        #list .
        paths_a = rclone_ls(".")
        #process local excludes (only for local branches)
        paths_a = filter_exclude_paths(os.getcwd(), paths_a)
        #list remote/path from conf file
        paths_b = rclone_ls(os.path.join(configuration.remote, rel_path))
        #compute all paths
        paths_all = merge_and_exclude_paths(paths_a, paths_b, rel_path, exclude_paths,
                                            configuration.global_excludes)
        #retrieve remote backup
        paths_b_backup = retrieve_backup(backup_config_path, rel_path)
        if paths_b_backup is None:
            raise UpBackException("No remote backup file found. Run with an init option")
        #compute operations
        operations = compute_operations(paths_all, paths_a, paths_b_backup, paths_b)
        logging.info("operations: "+str(operations))
        if operations.conflicts:
            write_conflicts(operations.conflicts, paths_a, paths_b)
            print("UpBack cannot perform the synchronization because of conflicts.")
            print("Please edit the "+UPBACK_CONFLICTS_FILE+" file and decide")
            print("how to manage conflicts, then run UpBack again.")
        else:
            if operations and not operations.is_empty():
                if configuration.verbose or configuration.interactive:
                    print(operations.pretty_format())
                if not configuration.interactive or \
                   raw_input("Proceed with these operations ? (Y/N) ").lower() == "y":
                    #perform operations
                    perform_operations(operations, paths_a, paths_b, configuration.remote, rel_path,
                                       configuration.no_backup, configuration.remote_backup,
                                       configuration.backup_suffix)
            #update remote backup
            save_backup(backup_config_path, configuration.remote)
    except UpBackException as exception:
        print(str(exception))
        return STATUS_ERROR
    finally:
        cleanup()
    return STATUS_OK
