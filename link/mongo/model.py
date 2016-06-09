# -*- coding: utf-8 -*-

from link.dbrequest.model import Cursor
from bson import json_util
import json


class MongoCursor(Cursor):
    def to_model(self, doc):
        jsondoc = json_util.dumps(doc)
        doc = json.loads(jsondoc)

        return super(MongoCursor, self).to_model(doc)

    def __len__(self):
        return self.cursor.count(True)

    def __next__(self):
        return self.to_model(self.cursor.next())
