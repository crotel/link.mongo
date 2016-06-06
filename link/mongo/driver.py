# -*- coding: utf-8 -*-

from b3j0f.conf import Configurable, category, Parameter
from link.dbrequest.driver import Driver
from link.mongo import CONF_BASE_PATH

from pymongo import MongoClient


@Configurable(
    paths='{0}/driver.conf'.format(CONF_BASE_PATH),
    conf=category(
        'MONGO',
        Parameter(name='auth_database', value=None),
        Parameter(name='auth_mechanism', value='SCRAM-SHA-1'),
        Parameter(name='auth_mechanism_props', value=None)
    )
)
class MongoDriver(Driver):

    __protocols__ = ['mongo']

    @property
    def database(self):
        if not hasattr(self, '_database'):
            database = self.path[1:].split('/', 1)[0]

            db = self.conn[database]

            if self.user is not None and self.pwd is not None:
                kwargs = {
                    'mechanism': self.auth_mechanism
                }

                if self.auth_database is not None:
                    kwargs['source'] = self.auth_database

                mechanismProps = self.auth_mechanism_props
                if mechanismProps is not None:
                    kwargs['authMechanismProperties'] = mechanismProps

                db.authenticate(
                    self.user,
                    password=self.pwd,
                    **kwargs
                )

            self._database = db

        return self._database

    @property
    def collection(self):
        if not hasattr(self, '_collection'):
            collection = self.path[1:].split('/', 1)[1]
            collection = collection.replace('/', '_')

            self._collection = self.database[collection]

        return self._collection

    def _connect(self):
        return MongoClient(self.hosts)

    def _disconnect(self, conn):
        del self._database
        del self._collection
        del conn

    def _isconnected(self, conn):
        return conn is not None

    def _process_query(self, conn, query):
        if query['type'] == Driver.QUERY_COUNT:
            ast = query['filter']
            mfilter = self.ast_to_filter(ast)

            return self.collection.count(mfilter)

        if query['type'] == Driver.QUERY_CREATE:
            ast = query['update']
            doc = self.ast_to_insert(ast)

            result = self.collection.insert_one(doc)
            doc['_id'] = result.inserted_id

            return doc

        elif query['type'] == Driver.QUERY_READ:
            ast = query['filter']
            mfilter = self.ast_to_filter(ast)

            return self.collection.find_many(mfilter)

        elif query['type'] == Driver.QUERY_UPDATE:
            filter_ast = query['filter']
            update_ast = query['update']

            mfilter = self.ast_to_filter(filter_ast)
            uspec = self.ast_to_update(update_ast)

            return self.collection.update_many(mfilter, uspec)

        elif query['type'] == Driver.QUERY_DELETE:
            ast = query['filter']
            mfilter = self.ast_to_filter(ast)

            return self.collection.delete_many(mfilter)

    def ast_to_insert(self, ast):
        raise NotImplementedError('TODO')

    def ast_to_filter(self, ast):
        raise NotImplementedError('TODO')

    def ast_to_update(self, ast):
        raise NotImplementedError('TODO')
