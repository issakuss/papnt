from typing import Optional, Dict, List
from pathlib import Path

from notion_client import Client

from .misc import load_config


class DatabaseInfo:
    def __init__(self, path_config: Optional[str | Path]=None):
        path_config = path_config or (Path(__file__).parent / 'config.ini')
        config = load_config(path_config)
        self.tokenkey = config['database']['tokenkey']
        self.database_id = config['database']['database_id']


class Database:
    def __init__(self, dbinfo: DatabaseInfo):
        self.notion = Client(auth=dbinfo.tokenkey)
        self.database_id = dbinfo.database_id

    def fetch_records(self, filter: Optional[dict]=None, debugmode: bool=False
                      ) -> List:
        records = []
        start_cursor = None
        while True:
            database = self.notion.databases.query(
                database_id=self.database_id, filter=filter,
                start_cursor=start_cursor)
            records += database['results']
            if not database['has_more']:
                self.db_results = records
                return self
            start_cursor = database['next_cursor']
            if debugmode:
                print('It is debugmode, records were fetched partly.')
                self.db_results = records
                return self

    def fetch_newest_record(self):
        return self.notion.databases.query(self.database_id, page_size=1)

    def update(self, page_id: str, prop: Dict):
        self.notion.pages.update(page_id=page_id, properties=prop)

    def create(self, prop: Dict):
        self.notion.pages.create(
            parent={'database_id': self.database_id}, properties=prop)
