#!/usr/bin/env python3

import logging
from .boolean_expression import BooleanExpression

default_condition = BooleanExpression()
default_expression = 'pass'

class Conditional:
    """If else conditional.
    desc        = description of conditional.
    attrib      = a dictionary of user-specified attributes
    condition   = boolean statement expression
    consequent  = expressions if condition is met
    elif_arr    = array of Conditionals for if-else expressions
    alternative = expressions if condition is not met
    indent_spaces = number of spaces in an indent
    """

    __slots__ = ('desc','attrib','condition','consequent','elif_arr','alternative','indent_spaces')

    def __init__(self,*,desc="",attrib={},condition=default_condition,consequent=[],\
                elif_arr=[],alternative=[],indent_spaces=4):
        self.desc        = desc          # description
        self.attrib      = attrib
        self.condition   = condition
        #assert isinstance(self.condition, BooleanExpression)


        self.consequent = consequent

        self.elif_arr = elif_arr
        for consequent in elif_arr:
            assert isinstance(consequent, Conditional)
            consequent.indent += 1

        if len(alternative) == 0:
            alternative.append(default_expression)
        self.alternative = alternative

        self.indent_spaces = indent_spaces
        if len(self.elif_arr) > 0 and len(self.alternative) == 0:
            raise ValueError('elif array cannot contain values while alternative does not')

    def __str__(self):
        single_level_indent = ' ' * self.indent_spaces
        conditional = ''.join([
                    'if ',
                    str(self.condition).strip(),
                    ':'
                   ])
        str_data = [conditional]

        if_expressions = [single_level_indent + line \
            for exp in self.consequent for line in str(exp).split('\n')]
        str_data.extend(if_expressions)

        elif_expressions = [str(exp) for exp in self.elif_arr]
        str_data.extend(elif_expressions)

        #str_data.append('else:')
        #else_expressions = [single_level_indent + line \
        #    for exp in self.consequent for line in str(exp).split('\n')]
        #str_data.extend(else_expressions)

        return '\n'.join(str_data)

    def __repr__(self):
        return ''.join([f'Conditional(condition: {repr(self.condition)}, consequent: ', \
                str([repr(exp) for exp in self.consequent]), 'elif_arr: ', \
                str([repr(elif_cond) for elif_cond in self.elif_arr]), ', alternative: ', \
                str([repr(exp) for exp in self.alternative]), ')'])

    def json_dict(self):
        return {
                "desc": self.desc,
                "attrib": self.attrib,
                "condition": self.condition.json_dict(),
                "consequent": [str(elem) for elem in self.consequent],
                "elif_arr": [elem.json_dict() for elem in self.elif_arr],
                "alternative": [str(elem) for elem in self.alternative]
               }

    def dump(self,func=print):
        func(str(self))

def main():
    conditional = Conditional()
    # print(repr(conditional))
    # print(conditional.json_dict())
    print(conditional)

if __name__ == '__main__':
    main()

