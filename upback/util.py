"""
Misc utilities
"""

import datetime
import os
import fnmatch

#TODO: implement a more refined matching
# e.g. wildcard/ only matches dirs
# and others similarly to .gitignore
def wildcard_match(item, wildcard):
    return fnmatch.fnmatch(item, wildcard)

def is_path_local(path):
    return not ":" in path

def parse_rfc3339(datetime_string):
    """ Returns a datetime object for
        a RFC3339-formatted string
    """
    timezone = "+0000"
    if datetime_string.endswith("Z"):
        datetime_string = datetime_string[0:-1]
    _, _, datetime_time_string = datetime_string.partition("T")
    zone_sep = ""
    if "+" in datetime_time_string:
        zone_sep = "+"
    elif "-" in datetime_time_string:
        zone_sep = "-"
    if not zone_sep == "":
        datetime_string, _, datetime_offset = datetime_string.partition(zone_sep)
        timezone = zone_sep+datetime_offset.replace(":", "")
    microseconds = 0
    if "." in datetime_time_string:
        datetime_string, _, datetime_ns = datetime_string.partition(".")
        microseconds = int(float("0."+datetime_ns)*1000)
    time_3339 = datetime.datetime.strptime(datetime_string, "%Y-%m-%dT%H:%M:%S")
    hours = int(timezone[1:3])
    minutes = int(timezone[3:5])
    timezone_delta = datetime.timedelta(hours=hours, minutes=minutes)
    if timezone[0] == '+':
        time_3339 -= timezone_delta
    else:
        time_3339 += timezone_delta
    time_3339 = time_3339.replace(microsecond=microseconds)
    return time_3339

def lock_file(path):
    """ Creates a lockfile
        Returns True if the lockfile was absent and has been created
        Returns False if the lockfile was already present
    """
    #TODO if open fails and the lockfile is present, check its creation date
    # and, if it's more than ??? remove it and retry
    # pylint: disable=global-statement
    try:
        lock_fd = os.open(path, os.O_CREAT | os.O_WRONLY | os.O_EXCL)
    except OSError:
        return False
    else:
        global LOCK_FILENAME
        LOCK_FILENAME = path
        os.close(lock_fd)
        return True

def remove_lock_file():
    """ Removes a previously created lockfile (if any) """
    # pylint: disable=global-statement
    global LOCK_FILENAME

    if LOCK_FILENAME is not None and os.path.isfile(LOCK_FILENAME):
        os.unlink(LOCK_FILENAME)

LOCK_FILENAME = None
