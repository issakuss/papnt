from typing import Literal, Optional, Dict, List
from pathlib import Path

from notion_client import Client


MAX_LEN_CHILDREN = 100


class NotionDatabase:
    def __init__(self, tokenkey: str, database_id: str):
        self.notion = Client(auth=tokenkey)
        self.database_id = database_id

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
        prop['info'] = {'checkbox': True}
        self.notion.pages.update(page_id=page_id, properties=prop)

    def update_record(self, page_id: str, prop: Dict,
                      children: Optional[List]=None):
        prop = prop | {'info': {'checkbox': True}}
        self.update_properties(page_id, prop)

        if children is None:
            children = []
        for i in range(0, len(children), MAX_LEN_CHILDREN):
            batch = children[i:i + MAX_LEN_CHILDREN]
            self.notion.blocks.children.append(
                block_id=page_id, children=batch)

    def create(self, prop: Dict, children: Optional[List]=None,
               check_info: bool=True):
        if children is None:
            children = []
        children_till_100 = children[:MAX_LEN_CHILDREN]
        if check_info:
            prop = prop | {'info': {'checkbox': True}}
        newpage = self.notion.pages.create(
            parent={'database_id': self.database_id},
            properties=prop, children=children_till_100)

        if len(children) <= MAX_LEN_CHILDREN:
            return

        children_from_100 = children[MAX_LEN_CHILDREN:]
        for i in range(0, len(children_from_100), MAX_LEN_CHILDREN):
            batch = children_from_100[i:i + MAX_LEN_CHILDREN]
            self.notion.blocks.children.append(
                block_id=newpage['id'],
                children=batch)

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
    database = NotionDatabase(DatabaseInfo())
    database.add_children(
        page_id=PAGEID, contents='test script', blocktype='paragraph')
