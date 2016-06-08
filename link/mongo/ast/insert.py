# -*- coding: utf-8 -*-

from link.dbrequest.expression import E
from b3j0f.task import gettask

from six import string_types


class ASTInsertTransform(object):

    OPERATOR_MAP = {
        E.ADD: lambda a, b: a + b,
        E.SUB: lambda a, b: a - b,
        E.MUL: lambda a, b: a * b,
        E.DIV: lambda a, b: a / b,
        E.MOD: lambda a, b: a % b,
        E.POW: lambda a, b: a ** b,
        E.BITLSHIFT: lambda a, b: a << b,
        E.BITRSHIFT: lambda a, b: a >> b,
        E.BITAND: lambda a, b: a & b,
        E.BITOR: lambda a, b: a | b,
        E.BITXOR: lambda a, b: a ^ b,
    }

    def __init__(self, ast, *args, **kwargs):
        super(ASTInsertTransform, self).__init__(*args, **kwargs)

        self.assignmentsByProp = {
            prop['val']: assign['val']
            for prop, assign in ast
            if assign['val'] is not None
        }

    def resolve_expression(self, prop):
        if isinstance(prop, string_types):
            prop = self.assignmentsByProp[prop]

        if isinstance(prop, dict):
            if prop['name'] == 'val':
                return prop['val']

            elif prop['name'] == 'ref':
                return self.resolve_expression(prop['val'])

            elif prop['name'] == 'func':
                return self.resolve_function(prop['val'])

        elif isinstance(prop, list):
            left, op, right = prop

            if left['name'] == 'ref':
                left = self.resolve_expression(left['val'])

            elif left['name'] == 'func':
                left = self.resolve_function(left['val'])

            elif left['name'] == 'val':
                left = left['val']

            if right['name'] == 'ref':
                right = self.resolve_expression(right['val'])

            elif right['name'] == 'func':
                right = self.resolve_function(right['val'])

            elif right['name'] == 'val':
                right = right['val']

            return ASTInsertTransform.OPERATOR_MAP[op['val']](left, right)

        else:
            return None

    def resolve_function(self, func):
        f = gettask('link.dbrequest.functions.{0}'.format(func['func']))
        args = [
            self.resolve_expression(argument)
            for argument in func['args']
        ]

        return f(*args)

    def __call__(self):
        return {
            prop: self.resolve_expression(assign)
            for prop, assign in self.assignmentsByProp.items()
        }
