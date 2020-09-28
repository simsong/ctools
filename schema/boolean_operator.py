#!/usr/bin/env python3

import logging

class BooleanOperator:
    """
    Boolean Operator

    desc    = description of conditional.
    attrib  = a dictionary of user-specified attributes
    op_type = operator type
    """

    __slots__ = ('desc','attrib','op_type')

    def __init__(self,*,desc="",attrib={},op_type=None):
        self.desc        = desc          # description
        self.attrib      = attrib
        self.set_type(op_type)

    def set_type(self, op_type):
        res = ""
        if op_type is None:
            res = None
        else:
            op_type = op_type.strip()
            if op_type in ["<=", ">=", "<", ">", "==", \
                "!=", "not", "and", "or"]:
                res = op_type
            else:
                raise ValueError(f'operator type {op_type} invalid')
        self.op_type = res

    def __eq__(self, other):
        if isinstance(other, BooleanOperator):
            return self.op_type == other.op_type
        return False

    def __str__(self):
        if self.op_type is None:
            return ''
        return self.op_type

    def __repr__(self):
        return f'Boolean Operator(type: {self.op_type})'

    def json_dict(self):
        return {
                "desc": self.desc,
                "attrib": self.attrib,
                "type": self.op_type
               }

    def dump(self,func=print):
        func(str(self))

def main():
    operator = BooleanOperator(op_type="<=")
    print(operator)

if __name__ == '__main__':
    main()

