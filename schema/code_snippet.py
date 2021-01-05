#!/usr/bin/env python3

import logging
from .boolean_expression import BooleanExpression
from .while_loop import WhileLoop
from .conditional import Conditional
from .variable_assignment import VariableAssignment

valid_expression_types = [WhileLoop, Conditional, VariableAssignment]

class CodeSnippet:
    """
    Code Snippet

<<<<<<< HEAD
    desc          = description of code snippet
    attrib        = user defined attributes
    name          = code snippet name
    expressions   = ordered list of loops, conditionals, and variable assignments
    indent_spaces = number of spaces in an indent
=======
    desc        = description of code snippet
    attrib      = user defined attributes
    name        = code snippet name
    expressions = ordered list of loops, conditionals, and variable assignments
>>>>>>> master

    note - there is no indent level for code snippets. if this is to be added later,
            you can use an indent_level=1 and indent_spaces=4, etc.
    """

    __slots__ = ('desc','attrib','name','expressions','indent_spaces', 'variables', 'variable_to_validate')

    def __init__(self,*,desc="",attrib={},name='',expressions=[], indent_spaces=4):

        self.desc        = desc          # description
        self.attrib      = attrib
        assert isinstance(name, str)
        if len(name) == 0:
            raise ValueError('name must be provided')
        if ' ' in name or '\"' in name or '\'' in name:
            raise ValueError('invalid characters in name found')
        self.name = name

        self.indent_spaces = indent_spaces

        self.expressions = []
        for exp in expressions:
            self.add_expression(exp)

        self.variables = []
        self.variable_to_validate = None

    def add_variable(self, variable):
        if variable.lower() not in self.variables:
            self.variables.append(variable.lower())

    def set_validation_variable(self, variable):
        self.variable_to_validate = variable.lower()

    def add_expression(self, expression):
        given_type = type(expression)
        if given_type not in valid_expression_types:
            raise TypeError(f'invalid expression type {given_type} provided')
        self.expressions.append(expression)

    def __str__(self):
        single_level_indent = ' ' * self.indent_spaces
        # outputs a function representation of the snippet
        str_data = [f'def snippet_{self.name}(row):']
        expressions = [single_level_indent + line \
            for exp in self.expressions for line in str(exp).split('\n')]
        str_data.extend(expressions)

        str_data += [f'    return row']


        return '\n'.join(str_data)

    def __repr__(self):
        return ''.join([f'Code Snippet(name: {self.name}, expressions: ', \

                str([repr(exp) for exp in self.expressions]), ')'])

    def json_dict(self):
        return {
                "desc": self.desc,
                "attrib": self.attrib,
                "name": self.name,
                "expressions": [str(elem) for elem in self.expressions],
                "variables": [var for var in self.variables]
               }

    def dump(self,func=print):
        func(str(self))


def main():
    snippet = CodeSnippet(name='snippet')
    snippet.add_expression(Conditional())
    print(repr(snippet))
    print(snippet.json_dict())
    print(snippet)


if __name__ == '__main__':
    main()

