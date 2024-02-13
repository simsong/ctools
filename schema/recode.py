# Recodes are implemented as compiled code. The function is put into the __main__ namespace.
# https://stackoverflow.com/questions/19850143/

import re


class Recode:
    """Represent a recode from one table to another.  A recode consists of two parts:
    DESTINATION=SOURCE
    Where DESTINATION is a python variable, ideally a TABLE[VARIABLE] form, but could be anything.
    Where SOURCE=A python statement that will be evaluated. (It is actually compiled). Any python may be used.
    Any use of TABLE[VARIABLE] may be provided; a row from TABLE must have bee read.
    """
    recode_re = re.compile(r"(\w+)\[(\w+)\]\s*=\s*(.*)")

    def __init__(self, name, desc, *, attrib={}):
        """@param name - The name of the recode, e.g. "recode1"
        @param desc - The description of the record, e.g. "A[T] = B[T]"
        """
        self.name = name
        m = self.recode_re.search(desc)
        if not m:
            raise RuntimeError("invalid Recode description: '{}'".format(desc))
        (self.dest_table_name, self.dest_table_var) = m.group(1, 2)
        self.statement = desc
        self.attrib = attrib
