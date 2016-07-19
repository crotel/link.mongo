# -*- coding: utf-8 -*-

from link.dbrequest.ast import NodeWalker
from link.dbrequest.expression import E
from six import string_types
from b3j0f.task import run


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


class UpdateWalker(NodeWalker):
    def resolve_expression(self, node, assignmentsByProp):
        if isinstance(node, string_types):
            node = assignmentsByProp[node]

        if node.name == 'val':
            return node.val

        elif node.name == 'ref':
            return self.resolve_expression(node.val, assignmentsByProp)

        elif node.name.startswith('func_'):
            return run({
                'name': 'link.dbrequest.functions.{0}'.format(node.name[5:]),
                'args': [
                    self.resolve_expression(arg, assignmentsByProp)
                    for arg in node.val
                ]
            })

        elif node.name.startswith('op_'):
            opname = node.name[3:]
            left, right = node.val

            left = self.resolve_expression(left, assignmentsByProp)
            right = self.resolve_expression(right, assignmentsByProp)

            operator = OPERATOR_MAP[opname]
            return operator(left, right)

    def walk_ASTAssign(self, node, children, assignmentsByProp):
        left, right = node.val

        assignmentsByProp[left.val] = right.val

    def walk_ASTInsert(self, node, children, assignmentsByProp):
        node.result = {
            prop: self.resolve_expression(expr)
            for prop, expr in assignmentsByProp.items()
        }

        return node.result

    def walk_ASTUpdate(self, node, children, assignmentsByProp):
        doc = {
            prop: self.resolve_expression(expr)
            for prop, expr in assignmentsByProp.items()
        }

        update_set = {
            prop: val
            for prop, val in doc.items()
            if val is not None
        }

        update_unset = {
            prop: val
            for prop, val in doc.items()
            if val is None
        }

        update = {}

        if update_set:
            update['$set'] = update_set

        if update_unset:
            update['$unset'] = update_unset

        node.result = update

        return node.result
