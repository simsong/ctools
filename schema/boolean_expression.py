#!/usr/bin/env python3

import logging
from .boolean_operator import BooleanOperator

default_condition=True

operators_before_first_element = [BooleanOperator(op_type='not')]

class BooleanExpression:
    """
    Boolean Expression

    desc        = description of conditional.
    attrib      = a dictionary of user-specified attributes
    first_element = first element in expression
    second_element = second element in expression (or None if no element)
    operator = boolean operator (and, or, not, <, >, <=, >=, ==, not, or None)
    """

    __slots__ = ('desc','attrib','first_element','second_element','operator')

    def __init__(self,*,desc="",attrib={},first_element=None,\
                second_element=None, operator=None):
        self.desc = desc # description
        self.attrib = attrib
        if first_element is None and second_element is not None:
            raise ValueError('second element provided without first')
        if first_element is None:
            first_element = str(True)
        assert isinstance(first_element, str)
        self.first_element  = first_element
        if second_element is not None:
            assert isinstance(second_element, str)
        self.second_element = second_element
        if operator is None:
            operator = BooleanOperator()
        assert isinstance(operator, BooleanOperator)
        self.operator = operator

    def __str__(self):
        elements = []
        elements.append(str(self.first_element.strip()))
        elements.append(str(self.operator))
        if self.operator in operators_before_first_element:
            elements.reverse()
        if self.second_element is not None:
            elements.append(str(self.second_element).strip())
        res = ' '.join(elements)
        return res

    def __repr__(self):
        return f'Boolean Expression(first element: {self.first_element}, ' + \
               f'operator: {repr(self.operator)}, second element: {self.second_element})'

    def json_dict(self):
        return {
                "desc": self.desc,
                "attrib": self.attrib,
                "first_element": self.first_element,
                "operator": self.operator.json_dict(),
                "second_element": self.second_element
               }

    def dump(self,func=print):
        func(str(self))

def main():
    exp = BooleanExpression()
    # print(repr(exp))
    # print(exp.json_dict())
    print(exp)

if __name__ == '__main__':
    main()

