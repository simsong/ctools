#!/usr/bin/env python3

import logging
from .variable import Variable
import z3

class VariableAssignment:
    """
    Variable Assignment

    desc     = description of variable assignment
    attrib   = a dictionary of user-specified attributes
    variable = boolean statement expression
    value    = value of variable
    solver   = z3 solver object
    """

    __slots__ = ('desc','attrib','variable','value','solver','z3_obj', 'second_element_is_variable')

    def __init__(self,variable,value,desc="",attrib={},\
                solver=None, second_element_is_variable=False):
        if desc:
            self.desc        = desc          # description
        if variable.desc:
            self.desc = variable.desc
        self.attrib      = attrib
        assert isinstance(variable, Variable)
        if variable.name is None:
            raise ValueError('variable name cannot be none')
        self.variable = variable
        self.second_element_is_variable = second_element_is_variable

        if solver:
            self.solver = solver
        self.set_value(value)

    def check_range(self):
        if self.z3_obj is None:
            raise RuntimeError('cannot find z3 object')
        if self.solver is None:
            raise RuntimeError('no z3 solver provided')

        for rangeval in self.variable.ranges:
            self.solver.add(self.z3_obj >= rangeval.a)
            self.solver.add(self.z3_obj <= rangeval.b)

    def set_value(self, value):
        if value is None:
            raise ValueError('value cannot be none in assignment')
        self.value = value
        if self.variable.python_type is None:
            self.z3_obj = None
            return
        if not isinstance(value, self.variable.python_type):
            raise ValueError(f'value is not of type {self.variable.python_type}')
        if self.variable.python_type == int:
            self.z3_obj = z3.Int(int(value))
        elif self.variable.python_type == bool:
            self.z3_obj = z3.Bool(bool(value))
        elif self.variable.python_type == float:
            self.z3_obj = z3.Float(float(value))
        elif self.variable.python_type == str:
            self.z3_obj = z3.String(str(value))
        elif self.variable.python_type == long:
            self.z3_obj = z3.Long(long(value))
        else:
            raise ValueError('invalid python type provided')

    def __str__(self):
        if not self.second_element_is_variable:
            str_data = [f"row['{self.variable.name.strip().lower()}']", ' = ', str(self.value).strip()]
        else:
            str_data = [f"row['{self.variable.name.strip().lower()}']", ' = ', f"row['{str(self.value).strip()}']"]

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

