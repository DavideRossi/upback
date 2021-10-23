"""
Package entry point
"""

import argparse
import logging
import sys

from .configuration import Configuration
from .upback import upback
from .const import *

def main():
    """ upback command line entry point """
    # pylint: disable=invalid-name,line-too-long
    # UpBack [{init-push|init-pull} remote [remote-backup-dir [remote-backup-suffix]]] [resume] [--rclone-path path] [--rclone-executable exec]
    #TODO improve this mess
    _parser = argparse.ArgumentParser(description="UpBack a file synchronization utility",
                                      usage="%(prog)s {[{init-push|init-pull} remote [remote-backup-dir [remote-backup-suffix]]]|[resume]} [-i] [-v] [-vv] [--rclone-path path] [--rclone-executable exec]")
    _parser.add_argument("--rclone-path")
    _parser.add_argument("--rclone-executable")
    _parser.add_argument("-i", action='store_true')
    _parser.add_argument("-v", action='store_true')
    _parser.add_argument("-vv", action='store_true')
    _arguments, _other_arguments = _parser.parse_known_args()
    if _other_arguments and (_other_arguments[0] == "init-push" or _other_arguments[0] == "init-pull"):
        _parser = argparse.ArgumentParser(description="UpBack a file synchronization utility", usage="%(prog)s [{init-push|init-pull} remote [remote-backup-dir [remote-backup-suffix]]] [--rclone-path path] [--rclone-executable exec]")
        _parser.add_argument("--force", action='store_true', help="Runs also if remote is not empty")
        _parser.add_argument("remote", help="The remote branch location in rclone syntax <remote>[:<path>]")
        _parser.add_argument("remote_backup_dir", metavar="remote_backup_dir", nargs="?", help="The backup path in remote where to store files that are overwritten")
        _parser.add_argument("remote_backup_suffix", metavar="remote_backup_suffix", nargs="?", help="The suffix for the files moved in the backup directory, defaults to the current date")
        _arguments = _parser.parse_args(_other_arguments[1:], _arguments)
        _arguments.__setattr__(_other_arguments[0].replace("-", "_"), True)
    elif _other_arguments and _other_arguments[0] == "resume":
        _arguments = _parser.parse_args(_other_arguments[1:], _arguments)
        _arguments.__setattr__("resume", True)
    else:
        _arguments = _parser.parse_args(_other_arguments, _arguments)
    _configuration = Configuration(_arguments)
    _log_level = logging.WARNING
    if _configuration.verbose_l2:
        _log_level = logging.INFO-1
    elif _configuration.verbose:
        _log_level = logging.INFO
    logging.basicConfig(format="%(message)s", level=_log_level)
    try:
        exit_status = upback()
    except KeyboardInterrupt:
        exit_status = STATUS_INTERRUPTED
    except SystemExit as e:
        if e.code != STATUS_OK:
            exit_status = STATUS_ERROR
    except Exception as e:
        print(e.message)
        exit_status = STATUS_ERROR
    sys.exit(exit_status)

if __name__ == '__main__':
    main()
