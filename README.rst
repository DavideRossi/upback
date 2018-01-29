UpBack
=======================

Two way filesystem synchronization utility based on
rclone <https://rclone.org>_.

UpBack assumes a star backup topology, that means it
can be used to keep one or more "local" filesystems (on
your laptop, workstation, workplace pc, etc...)
synchronized with a single "remote" backup.
rclone is used to access the remote storage so
you should be able to use UpBack with all the
cloud backup services supported by rclone (this
includes DropBox, Google Drive, Amazon Cloud Drive,
Microsoft OneDrive and others).
Before using UpBack the remote storage must be 
configured with rclone, here we assume the 
storage is accessible with name remote: so, for 
example, you should be able to list it by running:

rclone ls remote:

On first run you must tell UpBack the directory
on the remote to use for synchronization, the
local directory you run this from is assumed
as the local root of this backup branch:

upback init-push remote:backup

or

upback init-pull remote:backup

init-push copies the content of the local
branch to remote:backup (removing everyting
else from remote), init-pull copies from
local to remote. To avoid losing data
it is recommended to just run init from
an empty directory and make sure that
remote:backup is empty too.

UpBack always assumes you want to synchronize
from the current directory so the typical
invocation simply is:

upback

this will look for the configuration files
previously created with the init option
in the current dir or in one of its ancestor.
If the current directory is not the root
of a local branch only a partial synchronization
from the current level below will be performed.
This allows you to perform a partial synchronization
without the need to operate on the whole branch.
UpBack will then perform all the operations needed
so that the local and the remote branch are
synchornized without the risk of losing data
(that means that a file is overwritten only by
newer versions, or that a file is removed only
if it was removed from the other side and the
other side contains a fresher version of the 
files).
If this is not possible and a conflict is
detected UpBack aborts creating a conflict
file that you can edit.
One by one you can tell UpBack how to deal with 
that specific conflict (such as: the local version 
of a file is to be considered the good one, or both 
files in local and remote should be deleted, 
etc...).
Once the conflict file containts all the
resolutions you can resume UpBack

upback resume

`The source for this project is available here
<https://github.com/pypa/sampleproject>`_.

