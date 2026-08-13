"""Export every collection to JSON files that MongoDB Compass can import.

    python Database/export_json.py

Files land in Database/export/. Each one is a JSON array in MongoDB Extended
JSON format, so ObjectId and ISODate survive the round trip:

    { "_id": { "$oid": "..." }, "created_at": { "$date": "..." } }

To load them in Compass:
    1. Connect to mongodb://localhost:27017
    2. Create (or open) the database electromart_db
    3. Open a collection -> "Add Data" -> "Import JSON or CSV file"
    4. Pick the matching file, choose JSON, then Import

Import categories.json and brands.json before products.json, because product
documents reference the ids of those two collections.
"""
import io
import os

from bson.json_util import RELAXED_JSON_OPTIONS, dumps
from pymongo import MongoClient

MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
DB_NAME = os.environ.get('MONGO_DB_NAME', 'electromart_db')

# Order matters on import: products reference categories and brands.
COLLECTIONS = ['categories', 'brands', 'products']

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'export')


def export():
    db = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)[DB_NAME]
    os.makedirs(OUT_DIR, exist_ok=True)

    for name in COLLECTIONS:
        docs = list(db[name].find())
        path = os.path.join(OUT_DIR, name + '.json')
        with io.open(path, 'w', encoding='utf-8') as f:
            f.write(dumps(docs, indent=2, ensure_ascii=False,
                          json_options=RELAXED_JSON_OPTIONS))
        print('  %-14s %3d documents -> Database/export/%s.json (%.1f KB)'
              % (name, len(docs), name, os.path.getsize(path) / 1024))

    print('\nImport order in Compass: categories -> brands -> products')


if __name__ == '__main__':
    export()
