from typing import Optional, List
from pathlib import Path

from notion_client import Client

from .pdf2text import pdf2children
from .misc import load_config


# https://outpust.jp/blog/98701fc7-2af9-4c7b-b409-100be1a86092
class Page:
    def __init__(self, parent_id: str, path_config: Optional[str | Path]=None):
        path_config = path_config or (Path(__file__).parent / 'config.ini')
        config = load_config(path_config)
        self.notion = Client(auth=config['database']['tokenkey'])
        self.parent_id = parent_id
        ...

    def create_page(self, title: str, children: List[dict]):
        self.notion.pages.create(
            parent={'page_id': self.parent_id},
            properties={'title': [{'text': {'content': title}}]},
            children=children
        )


if __name__ == '__main__':
    children = pdf2children('./test/samplepdfs/sample1.pdf')
    page = Page('d5c90701b59e4c68b4d638bcb9271c4b')
    page.create_page('Test', children)
    