# -*- coding: utf-8 -*-

from link.dbrequest.driver import Driver

from link.mongo.ast.insert import ASTInsertTransform
from link.mongo.ast.filter import ASTFilterTransform
from link.mongo.model import MongoCursor


class MongoQueryDriver(Driver):

    cursor_class = MongoCursor

    def process_query(self, query):
        if query['type'] == Driver.QUERY_CREATE:
            ast = query['update']
            doc = self.ast_to_insert(ast)

            result = self.obj.insert(doc)
            doc['_id'] = result.inserted_id

            return doc

        elif query['type'] in [Driver.QUERY_READ, Driver.QUERY_COUNT]:
            ast = query['filter']
            mfilter, s = {}, slice(None)
            aggregation = False

            if ast:
                result = self.ast_to_filter(ast)

                if isinstance(result, tuple):
                    mfilter, s = result

                else:
                    aggregation = True

            if not aggregation:
                result = self.obj.find(mfilter, skip=s.start, limit=s.stop)

            else:
                result = self.obj.aggregate(result)

            if query['type'] == Driver.QUERY_COUNT:
                result = result.count()

            return result

        elif query['type'] == Driver.QUERY_UPDATE:
            filter_ast = query['filter']
            update_ast = query['update']

            mfilter, _ = self.ast_to_filter(filter_ast)
            uspec = self.ast_to_update(update_ast)

            result = self.obj.update(mfilter, uspec, multi=True)

            return result.modified_count

        elif query['type'] == Driver.QUERY_DELETE:
            ast = query['filter']
            mfilter, _ = self.ast_to_filter(ast)

            result = self.obj.delete(mfilter, multi=True)

            return result.deleted_count

    def ast_to_insert(self, ast):
        transform = ASTInsertTransform(ast)
        return transform()

    def ast_to_filter(self, ast):
        transform = ASTFilterTransform(ast)
        return transform()

    def ast_to_update(self, ast):
        doc = self.ast_to_insert(ast)

        update_set = {
            key: value
            for key, value in doc.items()
            if value is not None
        }

        update_unset = {
            key: value
            for key, value in doc.items()
            if value is None
        }

        update = {}

        if update_set:
            update['$set'] = update_set

        if update_unset:
            update['$unset'] = update_unset

        return update
