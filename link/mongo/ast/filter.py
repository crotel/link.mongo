# -*- coding: utf-8 -*-

from link.dbrequest.ast import NodeWalker
from link.dbrequest.expression import E

from copy import deepcopy
import re


CONDITION_OPERATOR_MAP = {
    '$lt': '<',
    '$lte': '<=',
    '$eq': '==',
    '$ne': '!=',
    '$gte': '>=',
    '$gt': '>'
}

EXPRESSION_OPERATOR_MAP = {
    E.ADD: '+',
    E.SUB: '-',
    E.MUL: '*',
    E.DIV: '/',
    E.MOD: '%',
    E.BITLSHIFT: '<<',
    E.BITRSHIFT: '>>',
    E.BITAND: '&',
    E.BITOR: '|',
    E.BITXOR: '^'
}


class FilterWalker(NodeWalker):
    def resolve_condition(self, node, operator):
        left, right = node.val

        if right.name == 'val':
            val = right.val

            if operator == '$regex':
                val = re.compile(right.val)

            return {
                left.val: {operator: val}
            }

        else:
            val = self.resolve_expression(right)

            if operator == '$regex':
                return {'$where': 'this.{0}.match({1})'.format(left.val, val)}

            else:
                return {'$where': 'this.{0} {1} {2}'.format(
                    left.val,
                    CONDITION_OPERATOR_MAP[operator],
                    val
                )}

    def resolve_expression(self, node):
        if node.name.startswith('op_'):
            operator = EXPRESSION_OPERATOR_MAP[node.name[3:]]
            left, right = node.val

            left = self.resolve_expression(left)
            right = self.resolve_expression(right)

            if operator == '**':
                return 'Math.pow({0}, {1})'.format(left, right)

            else:
                return '({0} {1} {2})'.format(left, operator, right)

        elif node.name == 'ref':
            return 'this.{0}'.format(node.val)

        elif node.name.startswith('func_'):
            return '{0}({1})'.format(
                node.name[5:],
                ', '.join([
                    self.resolve_expression(arg)
                    for arg in node.val
                ])
            )

        elif node.name == 'val':
            return '{0}'.format(node.val)

    def resolve_inverted(self, mfilter):
        mfilter = deepcopy(mfilter)

        for key in mfilter.keys():
            if key == '$and':
                mfilter['$or'] = self.resolve_inverted(mfilter.pop('$and'))

            elif key == '$or':
                mfilter['$and'] = self.resolve_inverted(mfilter.pop('$or'))

            else:
                subfilter = mfilter[key]

                if '$where' in subfilter:
                    subfilter['$where'] = '!({0})'.format(subfilter['$where'])

                elif '$regex' in subfilter:
                    subfilter['$not'] = subfilter.pop('$regex')

                else:
                    mfilter[key] = {'$not': subfilter}

        return mfilter

    def resolve_slices(self, nodes):
        start = 0
        stop = 0

        for s in nodes:
            sstart = s.val.start or 0
            sstop = s.val.stop or 0

            start = max(sstart, start)
            stop = min(sstop, stop)

        if start == 0:
            start = None

        if stop == 0:
            stop = None

        return start, stop

    def walk_ASTCondExists(self, node, children):
        node.result = self.resolve_condition(node, '$exists')
        return node.result

    def walk_ASTCondLt(self, node, children):
        node.result = self.resolve_condition(node, '$lt')
        return node.result

    def walk_ASTCondLte(self, node, children):
        node.result = self.resolve_condition(node, '$lte')
        return node.result

    def walk_ASTCondEq(self, node, children):
        node.result = self.resolve_condition(node, '$eq')
        return node.result

    def walk_ASTCondNe(self, node, children):
        node.result = self.resolve_condition(node, '$ne')
        return node.result

    def walk_ASTCondGte(self, node, children):
        node.result = self.resolve_condition(node, '$gte')
        return node.result

    def walk_ASTCondGt(self, node, children):
        node.result = self.resolve_condition(node, '$gt')
        return node.result

    def walk_ASTCondLike(self, node, children):
        node.result = self.resolve_condition(node, '$regex')
        return node.result

    def walk_ASTJoinAnd(self, node, children):
        left, right = node.val

        node.result = {
            '$and': [left.result, right.result]
        }

        return node.result

    def walk_ASTJoinOr(self, node, children):
        left, right = node.val

        node.result = {
            '$or': [left.result, right.result]
        }

        return node.result

    def walk_ASTJoinAnd(self, node, children):
        left, right = node.val

        node.result = {
            '$or': [
                {'$and': [left.result, right.result]},
                {'$and': [
                    self.resolve_inverted(left.result),
                    self.resolve_inverted(right.result)
                ]}
            ]
        }

        return node.result

    def walk_ASTFilter(self, node, children):
        node.result = node.val.result

        return node.result

    def walk_ASTExclude(self, node, children):
        node.result = self.resolve_inverted(node.val.result)

        return node.result

    def walk_ASTNot(self, node, children):
        node.result = self.resolve_inverted(node.val.result)

        return node.result

    def walk_ASTGroup(self, node, children):
        key = node.val[0]
        expressions = node.val[1:]

        group_stage = {
            '_id': '${0}'.format(key.val)
        }

        for expression in expressions:
            if expression.name.startswith('func_'):
                key = '{0}_{1}'.format(
                    expression.name[5:],
                    expression.val[0].val.replace('.', '_')
                )
                op = '${0}'.format(expression.name[5:])
                prop = '${0}'.format(expression.val[0].val)

                group_stage[key] = {op: prop}

        node.result = {'$group': group_stage}
        return node.result

    def walk_ASTQuery(self, node, children):
        mfilter = {'$and': [
            subnode.result
            for subnode in node.val
            if subnode.name == 'filter'
        ]}

        start, stop = self.resolve_slices([
            subnode
            for subnode in node.val
            if subnode.name == 'slice'
        ])

        grouping = node.val[-1] if node.val[-1].name == 'group' else None

        if grouping is not None:
            match_stage = {
                '$match': mfilter
            }

            if start is not None:
                match_stage['$skip'] = start

            if stop is not None:
                match_stage['$limit'] = stop

            return [match_stage, grouping.result]

        else:
            return mfilter, slice(start, stop)
