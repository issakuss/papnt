from typing import List
from copy import deepcopy
import re
from time import sleep
from pathlib import Path

from bs4 import BeautifulSoup
from bs4.element import Tag

from .misc import load_config
from grobid_client.grobid_client import GrobidClient


TEIURL = r'http://www.tei-c.org/ns/1.0'

class FigTabInfo:
    def __init__(self, arr: List):
        """tag, head, desc"""
        self.arr = arr

    def add_ids_insert(self, ids_insert: List[int]):
        self.arr = [[idx_insert] + col
                    for idx_insert, col in zip(ids_insert, self.arr)]
        return self

    def get_tags(self):
        if len(self.arr) == 0:
            return None
        for tag in list(zip(*self.arr[0])):
            yield tag

    def descend_by_indices(self):
        return sorted(self.arr, key=lambda x: x[0], reverse=True)


def _change_tag(soup, tag, new_tag_name: str):
    # https://www.lifewithpython.com/2020/07/python-processing-html-bs4.html
    new_tag = soup.new_tag(new_tag_name)
    new_tag.attrs = tag.attrs.copy()
    tag.wrap(new_tag)
    tag.unwrap()
    return new_tag


def _extr_xmltext(client: GrobidClient, load_path: str) -> str:
    # url = 'https://kermitt2-grobid.hf.space'  # DEMO URL provided by GROBID
    CFG = dict(
        generateIDs=False,
        consolidate_header=False,
        consolidate_citations=False,
        include_raw_citations=False,
        include_raw_affiliations=False,
        tei_coordinates=False,
        segment_sentences=False)
    _, _, text = client.process_pdf(
        'processFulltextDocument', str(load_path), **CFG)
    if text.startswith('[GENERAL] Could not create temprorary file'):
        raise RuntimeError('Check permission: ' + text)
    return text


def _make_simple_rich_text(text: List[str] | str) -> dict:
    if isinstance(text, str):
        text = [text]
    rich_text = []
    for text_ in text:
        rich_text.append({'text': {'content': text_}})
    return rich_text


def _make_paragraph_block(rich_text: List[dict] | str) -> dict:
    return {'object': 'block', 'paragraph': {'rich_text': rich_text}}


def _make_heading_block(text: str, level: int) -> dict:
    return {
        'object': 'block',
        'type': f'heading_{level}',
        f'heading_{level}': {
            'rich_text': [{'type': 'text', 'text': {'content': text}}]}}


def _extr_bib(soup: BeautifulSoup) -> dict:
    def extr_doi(bib: Tag) -> str:
        doi = bib.find('idno', {'type': 'DOI'})
        if doi is None:
            return ''
        return f'https://doi.org/{doi.get_text()}'

    bibs = soup.find_all('biblStruct', {'xml:id': True})
    return {bib['xml:id']: extr_doi(bib) for bib in bibs}


def _extr_elements(soup: Tag):
    bodyset = soup.find_all('div', {'xmlns': TEIURL})
    elements = []
    for bodies in bodyset:
        for body in bodies.find_all(['head', 'p']):
            elements.append(body)
    return elements

def _extr_figtab_info(figtabs: Tag) -> FigTabInfo:
    fig_info = []
    for figtab in figtabs:
        tag = figtab.get('xml:id', 'no_tag')
        head_elem = figtab.find('head')
        head = head_elem.get_text() if head_elem else ''
        desc_elem = figtab.find('figDesc')
        desc = desc_elem.get_text() if desc_elem else ''
        if desc.startswith(head):
            desc = desc[len(head):]
        fig_info.append([tag, head, desc])
    return FigTabInfo(fig_info)


def _extr_fig_info(soup: BeautifulSoup) -> FigTabInfo:
    figures = soup.find_all('figure', {'type': False})
    return _extr_figtab_info(figures)


def _extr_tab_info(soup: BeautifulSoup) -> FigTabInfo:
    tables = soup.find_all('figure', {'type': 'table'})
    return _extr_figtab_info(tables)


def _extr_table(soup: BeautifulSoup) -> dict:
    def tabletag2block(tabletag: Tag) -> str:
        def tabletag2strlist(table: Tag):
            rows = table.find_all('row')
            strlist = []
            for row in rows:
                strlist.append(
                    [cell.get_text() for cell in row.find_all('cell')])
            return strlist

        def table2block(table: List[List[str]]) -> dict:
            def row2child(row) -> List[dict]:
                cells = [_make_simple_rich_text(cell) for cell in row]
                return {'type': 'table_row',
                        'table_row': {'cells': cells}}
            if len(table) == 0:
                return {'type': 'table',
                        'table': {'table_width': 0,
                                  'children': []}}
            for i, series in enumerate(table):
                for ii, cell in enumerate(series):
                    if cell is None:
                        table[i][ii] = ''
            children = [row2child(list(row)) for row in zip(*table)]
            return {'type': 'table',
                    'table': {'table_width': len(list(zip(*table))[0]),
                              'children': children}}

        tabletag = tabletag2strlist(tabletag)
        return table2block(tabletag)

    tables = soup.find_all('figure', {'type': 'table'})
    blocks = dict()
    for table in tables:
        table_id = table['xml:id']
        table = table.find('table')
        blocks[table_id] = tabletag2block(table)
    return blocks


def _find_ids_insert(elements: List[BeautifulSoup], info: FigTabInfo
                     ) -> List[int]:
    ids_insert = []
    for tag in info.get_tags():
        for idx_insert, element in enumerate(elements):
            if element.find('ref', {'target': f'#{tag}'}):
                break
        ids_insert.append(idx_insert + 1)
    return ids_insert


def _insert_figtab(elements: List[BeautifulSoup], info: FigTabInfo
                   ) -> List[dict]:
    info = deepcopy(info)
    info.add_ids_insert(_find_ids_insert(elements, info)).descend_by_indices()
    for idx_insert, _, head, desc in info.arr:
        to_insert = BeautifulSoup(f'<p>{head} {desc}</p>', 'xml').find('p')
        elements.insert(idx_insert, to_insert)


def _insert_fig(elements: List[BeautifulSoup], fig_info: FigTabInfo
                ) -> List[dict]:
    return _insert_figtab(elements, fig_info)


def _insert_tab(elements: List[BeautifulSoup], info: FigTabInfo,
                tables: dict) -> List[dict]:
    _insert_figtab(elements, info)
    info = deepcopy(info)
    info.add_ids_insert(_find_ids_insert(elements, info)).descend_by_indices()
    for idx_insert, tag, _, _ in info.arr:
        elements.insert(idx_insert, tables[tag])


def _elements2children_biblink(elements: List, biblinks) -> List:
    def replace_biblink(element: Tag) -> BeautifulSoup:
        text = str(element)
        for key, link in biblinks.items():
            text = text.replace(f'<ref target="#{key}" type="bibr">',
                                f'<ref target="{link}" type="bibr">')
        element = BeautifulSoup(text, 'xml').find(element.name)
        for empty_link_tag in element.find_all('ref', {'target': ''}):
            empty_link_tag.unwrap()
        return element

    def split_texts_by_biblink(element: Tag) -> List[str] | None:
        if len(bibrefs := element.find_all('ref', {'type': 'bibr'})) == 0:
            return
        for bibref in bibrefs:
            _change_tag(element.parent, bibref, 'bibref')
        texts = re.split(r'<bibref |</bibref>', str(element))
        texts = [re.sub(r'<p>|</p>', '', text) for text in texts]
        return texts

    replaced = []
    for element in elements:
        if isinstance(element, dict):
            replaced.append(element)
            continue
        element = replace_biblink(element)
        texts = split_texts_by_biblink(element)
        if texts is None:
            replaced.append(element)
            continue
        pattern = r'target="(.*?)" type="bibr">'
        rich_text = []
        for text in texts:
            if (match := re.search(pattern, text)) is None:
                rich_text.append({'text': {'content': text}})
                continue
            rich_text.append({'text': {'content': re.sub(pattern, '', text),
                                       'link': {'url': match.group(1)}}})
        replaced.append(_make_paragraph_block(rich_text))
    return replaced


def _elements2children_heading(elements) -> List:
    children = []
    for element in elements:
        if isinstance(element, dict) or (element.name != 'head'):
            children.append(element)
            continue
        children.append(_make_heading_block(element.get_text(), 1))
    return children


def _elements2children_paragraph(elements: List) -> List[dict]:
    def split_text(text: str) -> List[str]:
        MAX_LENGTH_PARAGPRAH = 2000
        if len(text) <= MAX_LENGTH_PARAGPRAH:
            return [text]
        n_splits = (len(text) // MAX_LENGTH_PARAGPRAH) + 1
        ids_space = [m.start() for m in re.finditer(r' ', text)]
        ids_split = [ids_space[i * len(ids_space) // n_splits]
                     for i in range(1, n_splits)]
        split_texts = []
        idx_from = 0
        for idx_to in ids_split:
            split_texts.append(text[idx_from:idx_to] + '......')
            idx_from = idx_to + 1
        split_texts.append(text[idx_from:])
        return split_texts

    children = []
    for element in elements:
        if isinstance(element, dict):
            children.append(element)
            continue
        texts = split_text(element.get_text())
        for text in texts:
            rich_text = _make_simple_rich_text(text)
            children.append(_make_paragraph_block(rich_text))
    return children


def pdf2children(client: GrobidClient, load_path: str | Path) -> str | None:
    soup = BeautifulSoup(_extr_xmltext(client, load_path), 'xml')

    biblinks = _extr_bib(soup)
    fig_info = _extr_fig_info(soup)
    tab_info = _extr_tab_info(soup)
    tables = _extr_table(soup)

    elements = _extr_elements(soup)

    _insert_fig(elements, fig_info)
    _insert_tab(elements, tab_info, tables)
    elements = _elements2children_biblink(elements, biblinks)
    elements = _elements2children_heading(elements)
    children = _elements2children_paragraph(elements)
    return children


class PDF2ChildrenConverter:
    def __init__(self, url: str):
        if url == '':
            self.client = None
            return
        while True:
            try:
                self.client = GrobidClient(url)
            except:
                raise ConnectionError('Failed to connect to GORBID')
            break

    def convert(self, load_path_pdf: str | Path):
        if self.client:
            return pdf2children(self.client, load_path_pdf)
