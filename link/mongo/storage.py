# -*- coding: utf-8 -*-

from link.middleware.connectable import ConnectableMiddleware
from link.middleware.core import register_middleware
from link.feature import addfeatures

from link.mongo.driver import MongoQueryDriver

from pymongo import MongoClient


@register_middleware
@addfeatures([MongoQueryDriver])
class MongoStorage(ConnectableMiddleware):

    __protocols__ = ['mongo']

    def __init__(
        self,
        auth_database=None,
        auth_mechanism='SCRAM-SHA-1',
        auth_mechanism_props=None,
        *args, **kwargs
    ):
        super(MongoStorage, self).__init__(*args, **kwargs)

        self.auth_database = auth_database
        self.auth_mechanism = auth_mechanism
        self.auth_mechanism_props = auth_mechanism_props

    @property
    def database(self):
        if not hasattr(self, '_database'):
            database = self.path[0]

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
            collection = '_'.join(self.path[1:])

            self._collection = self.database[collection]

        return self._collection

    def _connect(self):
        return MongoClient(['{0}:{1}'.format(*host) for host in self.hosts])

    def _disconnect(self, conn):
        del self._database
        del self._collection
        del conn

    def _isconnected(self, conn):
        return conn is not None

    def insert(self, docs):
        one = False

        if not isinstance(docs, list):
            one = True
            docs = [docs]

        result = self.collection.insert_many(docs)

        for doc, _id in zip(docs, result.inserted_ids):
            doc['_id'] = _id

        if one:
            docs = docs[0]

        return docs

    def find(self, mfilter, skip=None, limit=None):
        result = self.collection.find(mfilter)

        if skip is not None:
            result = result.skip(skip)

        if limit is not None:
            result = result.limit(limit)

        return result

    def count(self, mfilter, skip=None, limit=None):
        return self.find(mfilter, skip=skip, limit=limit).count()

    def update(self, mfilter, spec, multi=True):
        if multi:
            result = self.collection.update_many(mfilter, spec)

        else:
            result = self.collection.update_one(mfilter, spec)

        return result.modified_count

    def delete(self, mfilter, multi=True):
        if multi:
            result = self.collection.delete_many(mfilter)

        else:
            result = self.collection.delete_one(mfilter)

        return result.deleted_count

    def aggregate(self, pipeline):
        return self.collection.aggregate(pipeline)
