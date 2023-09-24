#!/usr/bin/env python3

import logging
from .boolean_expression import BooleanExpression

default_expression = 'pass'
default_condition = BooleanExpression()


class WhileLoop:
    """
    While Loop

    desc        = description of conditional.
    attrib      = a dictionary of user-specified attributes
    condition   = boolean statement expression
    consequent  = expressions if condition is met
    indent_spaces = number of spaces in an indent
    """

    __slots__ = ('desc', 'attrib', 'condition', 'consequent', 'indent_spaces')

    def __init__(self, *, desc="", attrib={}, condition=default_condition, consequent=[],
                 indent_spaces=4):
        self.desc = desc          # description
        self.attrib = attrib
        self.condition = condition
        assert isinstance(self.condition, BooleanExpression)

        if len(consequent) == 0:
            consequent.append(default_expression)
        self.consequent = consequent

        self.indent_spaces = indent_spaces

    def __str__(self):
        single_level_indent = ' ' * self.indent_spaces
        conditional = ''.join([
            'while ',
            str(self.condition).strip(),
            ':'
        ])
        str_data = [conditional]

        expressions = [single_level_indent + line
                       for exp in self.consequent for line in str(exp).split('\n')]
        str_data.extend(expressions)

        return '\n'.join(str_data)

    def __repr__(self):
        return ''.join([f'While Loop(condition: {repr(self.condition)}, consequent: ',
                        str([repr(exp) for exp in self.consequent]), ')'])

    def json_dict(self):
        return {
            "desc": self.desc,
            "attrib": self.attrib,
            "condition": self.condition.json_dict(),
            "consequent": [str(elem) for elem in self.consequent]
        }

    def dump(self, func=print):
        func(str(self))


def main():
    loop = WhileLoop()
    print(loop)


if __name__ == '__main__':
    main()
