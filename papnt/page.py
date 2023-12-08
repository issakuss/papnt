from typing import Optional, List
import re
from pathlib import Path

from notion_client import Client

from .pdf2text import pdf2text
from .misc import load_config


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


def md2children(texts: str):
    # https://developers.notion.com/reference/block
    def make_text(text: str) -> dict:
        def split_text(text: str) -> List[str]:
            SPLIT = '__SPLITMARK__'
            if SPLIT in text:
                raise ValueError()

            APILIMIT = 2000
            if len(text) >= APILIMIT:
                text = text[:APILIMIT - 1] + SPLIT + text[APILIMIT - 1:]

            # By bibref
            text = text.replace('<__bibref__', SPLIT + '<__bibref__')
            text = text.replace('</__bibref__>', '</__bibref__>' + SPLIT)
            return text.split(SPLIT)

        def make_text_prop(text: str) -> dict:
            if re.search('<__bibref.*?</__bibref__>', text) is None:
                return {'type': 'text', 'text': {'content': text}}
            reftarget = re.findall(r'target="([^"]*)"', text)[0]
            pattern = '(<__bibref([^>]+)>)|(</__bibref__>)'
            if reftarget == '':
                return {'type': 'text', 'text': {
                    'content': re.sub(pattern, '', text)}}
            return {'type': 'text',
                    'text': {
                        'content': re.sub(pattern, '', text),
                        'link': {'url': reftarget}}}

        text_split = split_text(text)
        return {
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [make_text_prop(text) for text in text_split]}}

    def make_heading(text: str, level: int) -> dict:
        return {
            'object': 'block',
            'type': f'heading_{level}',
            f'heading_{level}': {
                'rich_text': [{'type': 'text', 'text': {'content': text}}]}}

    def md2child(text: str) -> dict:
        if text.startswith('# '):
            return make_heading(text.strip('# '), 1)
        elif text.startswith('## '):
            return make_heading(text.strip('# '), 2)
        elif text.startswith('### '):
            return make_heading(text.strip('# '), 3)
        else:
            return make_text(text)

    return [md2child(text) for text in texts.split('\n\n') if text]

if __name__ == '__main__':
    text = pdf2text('./test/samplepdfs/sample1.pdf')
    # text = 'aiueo<ref type="bibr" target="https://google.com">kakiku</ref>keko'
    children = md2children(text)

    page = Page('d5c90701b59e4c68b4d638bcb9271c4b')
    page.create_page('Test', children)
    