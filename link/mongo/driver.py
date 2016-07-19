# -*- coding: utf-8 -*-

from link.dbrequest.ast import ModelBuilder, AST
from link.dbrequest.driver import Driver

from link.mongo.ast.insert import UpdateWalker
from link.mongo.ast.filter import FilterWalker
from link.mongo.model import MongoCursor


class MongoQueryDriver(Driver):

    cursor_class = MongoCursor

    def __init__(self, *args, **kwargs):
        super(MongoQueryDriver, self).__init__(*args, **kwargs)

        self.mbuilder = ModelBuilder()
        self.wfilter = FilterWalker()
        self.wupdate = UpdateWalker()

    def process_query(self, query):
        if query['type'] == Driver.QUERY_CREATE:
            ast = AST('insert', query['update'])
            doc = self.wupdate.walk(self.mbuilder.parse(ast), {})

            return self.obj.insert(doc)

        elif query['type'] in [Driver.QUERY_READ, Driver.QUERY_COUNT]:
            ast = query['filter']
            mfilter, s = {}, slice(None)
            aggregation = False

            if ast:
                ast = AST('query', ast)
                result = self.wfilter.walk(self.mbuilder.parse(ast))

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
            filter_ast = AST('query', query['filter'])
            update_ast = AST('update', query['update'])

            mfilter, _ = self.wfilter.walk(self.mbuilder.parse(filter_ast))
            uspec = self.wupdate.walk(self.mbuilder.parse(update_ast), {})

            result = self.obj.update(mfilter, uspec, multi=True)

            return result.modified_count

        elif query['type'] == Driver.QUERY_DELETE:
            ast = AST('query', query['filter'])
            mfilter, _ = self.wfilter.walk(self.mbuilder.parse(ast))

            result = self.obj.delete(mfilter, multi=True)

            return result.deleted_count
