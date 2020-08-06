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

    desc        = description of code snippet
    attrib      = user defined attributes
    name        = code snippet name
    expressions = ordered list of loops, conditionals, and variable assignments
    
    note - there is no indent level for code snippets. if this is to be added later,
            you can use an indent_level=1 and indent_spaces=4, etc.
    """

    __slots__ = ('desc','attrib','name','expressions')

    def __init__(self,*,desc="",attrib={},name='',expressions=[]):
        self.desc        = desc          # description
        self.attrib      = attrib
        assert isinstance(name, str)
        if len(name) == 0:
            raise ValueError('name must be provided')
        self.name = name

        self.expressions = []
        for exp in expressions:
            self.add_expression(exp)

    def add_expression(self, expression):
        given_type = type(expression)
        if given_type not in valid_expression_types:
            raise TypeError(f'invalid expression type {given_type} provided')
        self.expressions.append(expression)

    def __str__(self):
        str_data = []

        expressions = [line for exp in self.expressions for line in str(exp).split('\n')]
        str_data.extend(expressions)

        return '\n'.join(str_data)

    def __repr__(self):
        return ''.join([f'Code Snippet(nam: {self.name}, expressions: ', \
                str([repr(exp) for exp in self.expressions]), ')'])

    def json_dict(self):
        return {
                "desc": self.desc,
                "attrib": self.attrib,
                "name": self.name,
                "expressions": [str(elem) for elem in self.expressions]
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

