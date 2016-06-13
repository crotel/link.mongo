# -*- coding: utf-8 -*-

from link.dbrequest.model import Cursor

from pymongo.command_cursor import CommandCursor
from bson import json_util
import json


class MongoCursor(Cursor):

    __slots__ = Cursor.__slots__ + ('_result', '_iterator')

    def __init__(self, *args, **kwargs):
        super(MongoCursor, self).__init__(*args, **kwargs)

        if isinstance(self.cursor, CommandCursor):
            self._result = list(self.cursor)
            self._iterator = iter(self._result)

        else:
            self._result = None
            self._iterator = None

    def to_model(self, doc):
        jsondoc = json_util.dumps(doc)
        doc = json.loads(jsondoc)

        return super(MongoCursor, self).to_model(doc)

    def __iter__(self):
        if self._result is not None:
            return self._iterator

        else:
            return self

    def __len__(self):
        if self._result is not None:
            return len(self._result)

        else:
            return self.cursor.count(True)

    def __next__(self):
        return self.to_model(self.cursor.next())

    def __getitem__(self, idx):
        if self._result is not None:
            return self._result[idx]

        else:
            return self.cursor[idx]
