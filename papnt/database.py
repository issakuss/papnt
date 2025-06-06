from typing import Literal, Optional, Dict, List
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

    def update_properties(self, page_id: str, prop: Dict):
        self.notion.pages.update(page_id=page_id, properties=prop)

    def create(self, prop: Dict):
        return self.notion.pages.create(
            parent={'database_id': self.database_id}, properties=prop)

    def add_children(self, page_id: str, contents: str | List | None,
                     blocktype: Literal['paragraph'], title: str='title'):
        def make_text(text: str):
            return {'rich_text': [{'type': 'text', 'text': {'content': text}}]}

        def make_block(contents: str,
                       blocktype: Literal['paragraph', 'toggle']):
            block = {'object': 'block'}
            match blocktype:
                case 'paragraph':
                    if isinstance(contents, str):
                        contents = make_text(contents)
                    block |= {'type': blocktype,
                              'paragraph': contents}
                    return block
                case 'toggle':
                    block |= {'type': blocktype,
                              'toggle': make_text(title) |
                                        {'children': contents}}
                    return block

                case _:
                    raise RuntimeError(
                        f'{blocktype} type block is not supported.')

        if contents is None:
            return
        self.notion.blocks.children.append(
            block_id=page_id, children=[make_block(contents, blocktype)])


if __name__ == '__main__':
    PAGEID = '16dbcba025d580359e95c5c37fd2d25c'
    database = Database(DatabaseInfo())
    database.add_children(
        page_id=PAGEID, contents='test script', blocktype='paragraph')
