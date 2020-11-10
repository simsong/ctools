#!/usr/bin/env python3

import logging
from .variable import Variable

# Z3 is now only imported if it is needed
# to prevent errors when z3 is not available

class VariableAssignment:
    """
    Variable Assignment

    desc     = description of variable assignment
    attrib   = a dictionary of user-specified attributes
    variable = boolean statement expression
    value    = value of variable
    solver   = z3 solver object
    """

    __slots__ = ('desc','attrib','variable','value','solver','z3_obj')

    def __init__(self,variable,value,desc="",attrib={}, solver=None):
        self.desc        = desc          # description
        self.attrib      = attrib
        assert isinstance(variable, Variable)
        if variable.name is None:
            raise ValueError('variable name cannot be none')
        self.variable = variable

        self.solver = solver
        self.set_value(value)

    def check_range(self):
        if self.z3_obj is None:
            raise RuntimeError('cannot find z3 object')
        if self.solver is None:
            raise RuntimeError('no z3 solver provided')

        for range_val in self.variable.ranges:
            self.solver.add(self.z3_obj >= range_val.a)
            self.solver.add(self.z3_obj <= range_val.b)

    def set_value(self, value):
        import z3
        if value is None:
            raise ValueError('value cannot be none in assignment')
        self.value = value
        if self.variable.python_type is None:
            self.z3_obj = None
            return
        if not isinstance(value, self.variable.python_type):
            raise ValueError(f'value is not of type {self.variable.python_type}')
        if self.python_type == int:
            self.z3_obj = z3.Int(int(value))
        elif self.python_type == bool:
            self.z3_obj = z3.Bool(bool(value))
        elif self.python_type == float:
            self.z3_obj = z3.Float(float(value))
        elif self.python_type == str:
            self.z3_obj = z3.String(str(value))
        else:
            raise ValueError('invalid python type provided')

    def __str__(self):
        str_data = [self.variable.name.strip(), ' = ', str(self.value).strip()]
        return ''.join(str_data)

    def __repr__(self):
        return ''.join([f'Variable Assignment(variable: {repr(self.variable)}, value: ', \
                str(self.value)])

    def json_dict(self):
        return {
                "desc": self.desc,
                "attrib": self.attrib,
                "variable": self.variable.json_dict(),
                "value": str(self.value)
               }

    def dump(self,func=print):
        func(str(self))

def main():
    var = Variable(name='test')
    assignment = VariableAssignment(var, 5)
    print(repr(assignment))
    print(assignment.json_dict())
    print(assignment)

if __name__ == '__main__':
    main()
