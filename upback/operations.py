"""
Operations class, use to represent synch operations to be performed
"""

class Operations(object):
    """ Operations to perform to achieve synchronization
    """
    def __init__(self):
        self.copy_a_to_b = []
        self.copy_b_to_a = []
        self.delete_from_a = []
        self.delete_from_b = []
        self.conflicts = []

    def add_copy_a_to_b(self, path, backup=False):
        self.copy_a_to_b.append((path, backup))

    def add_copy_b_to_a(self, path, backup=False):
        self.copy_b_to_a.append((path, backup))

    def add_delete_from_a(self, path, backup=False):
        self.delete_from_a.append((path, backup))

    def add_delete_from_b(self, path, backup=False):
        self.delete_from_b.append((path, backup))

    def add_conflict(self, path, explaination):
        self.conflicts.append((path, explaination))

    def is_empty(self):
        return len(self.copy_a_to_b) == 0 and \
               len(self.copy_b_to_a) == 0 and \
               len(self.delete_from_a) == 0 and \
               len(self.delete_from_b) == 0 and \
               len(self.conflicts) == 0

    def pretty_format_list(self, list):
        msg = ""
        for item in list:
            path, _ = item
            msg += "  "+path+"\n"
        return msg

    def pretty_format(self):
        msg = ""
        if self.conflicts:
            msg += "conflicts:\n"
            msg += self.pretty_format_list(self.conflicts)
        else:
            if self.copy_a_to_b:
                msg += "copy from local to remote:\n"
                msg += self.pretty_format_list(self.copy_a_to_b)
            if self.copy_b_to_a:
                msg += "copy from remote to local:\n"
                msg += self.pretty_format_list(self.copy_b_to_a)
            if self.delete_from_a:
                msg += "delete from local:\n"
                msg += self.pretty_format_list(self.delete_from_a)
            if self.delete_from_b:
                msg += "delete from remote:\n"
                msg += self.pretty_format_list(self.delete_from_b)
        return msg

    def __str__(self):
        return("copy from local to remote: "+str(self.copy_a_to_b)+
               "\ncopy from remote to local:"+str(self.copy_b_to_a)+
               "\ndelete from local: "+str(self.delete_from_a)+
               "\ndelete from remote: "+str(self.delete_from_b)+
               "\nconflicts: "+str(self.conflicts))
