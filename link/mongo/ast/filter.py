# -*- coding: utf-8 -*-

from link.dbrequest.comparison import C
from link.dbrequest.expression import E

import re


class ASTFilterTransform(object):

    CONDITION_MAP = {
        C.EXISTS: '$exists',
        C.LT: '$lt',
        C.LTE: '$lte',
        C.EQ: '$eq',
        C.NE: '$ne',
        C.GTE: '$gte',
        C.GT: '$gt',
        C.LIKE: '$regex'
    }

    def __init__(self, ast, *args, **kwargs):
        super(ASTFilterTransform, self).__init__(*args, **kwargs)

        self.filters = [
            clause
            for clause in ast
            if clause['name'] == 'filter'
        ]

        self.slices = [
            clause
            for clause in ast
            if clause['name'] == 'slice'
        ]

    def resolve_filter(self, clause, inverted=False):
        if isinstance(clause, dict) and clause['name'] == 'not':
            return self.resolve_filter(clause['val'], inverted=True)

        else:
            left, op, right = clause

            if op['name'] == 'join':
                left = self.resolve_filter(left, inverted=inverted)
                right = self.resolve_filter(right, inverted=inverted)

                if left and right:
                    if op['val'] == '&':
                        if inverted:
                            return {'$or': [left, right]}

                        else:
                            return {'$and': [left, right]}

                    elif op['val'] == '|':
                        if inverted:
                            return {'$and': [left, right]}

                        else:
                            return {'$or': [left, right]}

                elif left and not right:
                    return left

                elif right and not left:
                    return right

            elif op['name'] == 'cond':
                condop = ASTFilterTransform.CONDITION_MAP[op['val']]

                if isinstance(right, dict) and right['name'] == 'val':
                    val = right['val']

                    if condop == '$regex':
                        val = re.compile(right['val'])

                        if inverted:
                            return {left['val']: {'$not': val}}

                        else:
                            return {left['val']: {'$regex': val}}

                    if inverted:
                        return {left['val']: {'$not': {condop: val}}}

                    else:
                        return {left['val']: {condop: val}}

                else:
                    return {
                        '$where': self.resolve_condition(
                            left['val'],
                            op['val'],
                            right,
                            inverted=inverted
                        )
                    }

    def resolve_condition(self, propname, cond, expression, inverted=False):
        val = self.resolve_expression(expression)

        if cond == C.LIKE:
            where = 'this.{0}.match({1})'.format(propname, val)

        else:
            where = 'this.{0} {1} {2}'.format(propname, cond, val)

        if inverted:
            where = '!({0})'.format(where)

        return where

    def resolve_expression(self, expression):
        if isinstance(expression, dict):
            if expression['name'] == 'val':
                return '{0}'.format(expression['val'])

            elif expression['name'] == 'ref':
                return 'this.{0}'.format(expression['val'])

            elif expression['name'] == 'func':
                return '{0}({1})'.format(
                    expression['val']['name'],
                    ', '.join([
                        self.resolve_expression(argument)
                        for argument in expression['val']['args']
                    ])
                )

        elif isinstance(expression, list):
            left, op, right = expression[0]

            left = self.resolve_expression(left)
            right = self.resolve_expression(right)

            if op['val'] == E.POW:
                return 'Math.pow({0}, {1})'.format(left, right)

            else:
                return '{0} {1} {2}'.format(left, op['val'], right)

    def __call__(self):
        mfilter = {
            '$and': [
                self.resolve_filter(clause)
                for clause in self.filters
            ]
        }

        start = 0
        stop = 0

        for s in self.slices:
            sstart = s['val'].start or 0
            sstop = s['val'].stop or 0

            start = max(sstart, start)
            stop = min(sstop, stop)

        return mfilter, slice(start, stop)
