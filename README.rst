UpBack
======

Two way filesystem synchronization utility based on
rclone https://rclone.org.

UpBack assumes a star backup topology, that means it can be used to keep one or more "local" filesystem branches (on your laptop, workstation, workplace pc, etc...) synchronized with a single "remote" backup.
rclone is used to access the remote storage so you should be able to use UpBack with all the cloud backup services supported by rclone (this includes DropBox, Google Drive, Amazon Cloud Drive, Microsoft OneDrive and others). Before using UpBack the remote storage must be configured with rclone.

Status
------
In its current form UpBack is far from being production-ready code: *USE IT AT YOUR OWN RISK*. 
It is published mainly to be tested and gather bug reports and feedbacks.

Installation
------------
First of all you must install rclone. See https://rclone.org/install/ for details.
Here we assume rclone is installed and configured with a storage that is accessible with name remote: so, for example, you should be able to list it by running:
::
  rclone ls remote:

UpBack is written in Python and the easiest way to install it is to use Python's own packaging/distribution infrastructure. That means that, if you have Python (currently only version 2.7 is supported), you should be able to install UpBack for your user with:
::
  pip install --user git+https://github.com/DavideRossi/upback.git

Alternatively download the git repository as a zipfile ("Clone or download" green button on the top left on https://github.com/DavideRossi/upback then select "Download ZIP"), expand it, and from the upper upback directory run:
::
  pip install --user .

Usage
-----
On first run you must tell UpBack the directory on the remote to use for synchronization, the local directory you run this from is assumed to be local root of this backup branch:
::
  upback init-push remote:backup

or:
::
  upback init-pull remote:backup

init-push copies the content of the local branch to remote:backup (removing everything else from remote), init-pull copies from local to remote. 
To avoid losing data it is recommended to just run init from an empty directory and make sure that remote:backup is empty too.

UpBack always assumes you want to synchronize from the current directory so the typical invocation simply is:
::
  upback

this will look for the configuration files previously created with the init option in the current dir or in one of its ancestors.
If the current directory is not the root of a local branch only a partial synchronization from the current level and below will be performed.
This allows you to perform a partial synchronization without the need to operate on the whole branch.
UpBack will then perform all the operations needed so that the local and the remote branches are synchronized without the risk of losing data (that means that a file is overwritten only by newer versions, or that a file is removed only if it was removed from the other side and the other side contains a fresher version of the  files).
If this is not possible and a conflict is detected UpBack aborts creating a conflict file that you can edit.
One by one you can tell UpBack how to deal with a conflict (such as: the local version of a file is to be considered the good one, or both files in local and remote should be deleted, etc...).
Once the conflict file contains all the resolutions you can resume UpBack:
::
  upback resume

Common options
--------------
There are several command line options that can be used to configure the behavior of UpBack.
The most common ones are:

* -v
verbose. Prints various information on what UpBack is doing.

* -vv
more verbose.

* -i
interactive. Asks before performing synchronization operations.

Exclude (ignore) files and directories
--------------------------------------
There are two ways to exclude single files or whole branches from the fileset that is synchronized.
The first way is to use the "global_excludes" field in .upback.config. This is simply a list of the (relative path of the) elements that should not be considered.
The second way is to use .upback.exclude files.
Each line in a .upback.exclude file is a pattern against which elements in THE SAME directory containing the .upback.exclude are matched. 
If the match succeeds the element (can be a file or a sub directory) is ignored.
Of course, in the case of a sub directory, everything inside that sub directory is ignored as well.
Notice that this applies only to elements of a local filesystem; .upback.exclude in remote filesystems are NOT processed.

FAQ
---
* Are symlinks supported?
No, symlinks are deliberately skipped. 
If you need them consider to store the "real" files and directories in the local backup branch and link to it from somewhere else.
For example, if you want to backup a src/myproject directory that is outside an UpBack backup branch, put the real myproject directory inside the local UpBack branch, then link it from src/.

* What happens if I decide to ignore a conflict
One of the options that can be specified in the conflict file is to ignore a path.
Be aware that, the next time you run UpBack it will keep complaining about that conflict until you finally decide how to handle it.

* How do I report a bug?
Please use github's issue tracker https://github.com/DavideRossi/upback/issues

* What is that .upback.config file I see on the local root of an UpBack branch?
This is a configuration file storing the details about the backup branch. It is a JSON file and can be edited.

* What is that .upback.remote file I see on the local root of an UpBack branch?
That is the last contents of the remote branch seen by UpBack, it is used to decide which operations on the remote branch are to be considered new with respect to the last time UpBack has been executed.
