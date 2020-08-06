#!/usr/bin/env python3

import logging
from boolean_expression import BooleanExpression

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

        for expression of expressions:
            
        self.expressions = expressions

    def __str__(self):
        single_level_indent = ' ' * self.indent_spaces
        conditional = ''.join([
                    'while ',
                    str(self.condition).strip(),
                    ':'
                   ])
        str_data = [conditional]

        expressions = [single_level_indent + line \
            for exp in self.consequent for line in str(exp).split('\n')]
        str_data.extend(expressions)

        return '\n'.join(str_data)

    def __repr__(self):
        return ''.join([f'While Loop(condition: {repr(self.condition)}, consequent: ', \
                str([repr(exp) for exp in self.consequent]), ')'])

    def json_dict(self):
        return {
                "desc": self.desc,
                "attrib": self.attrib,
                "condition": self.condition.json_dict(),
                "consequent": [str(elem) for elem in self.consequent]
               }

    def dump(self,func=print):
        func(str(self))

def main():
    loop = WhileLoop()
    # print(repr(loop))
    # print(loop.json_dict())
    print(loop)

if __name__ == '__main__':
    main()

