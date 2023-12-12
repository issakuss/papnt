from typing import List
import re
import subprocess
from time import sleep
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup
from bs4.element import Tag

from grobid_client.grobid_client import GrobidClient


TEIURL = r'http://www.tei-c.org/ns/1.0'


def _change_tag(soup, tag, new_tag_name: str):
    # https://www.lifewithpython.com/2020/07/python-processing-html-bs4.html
    new_tag = soup.new_tag(new_tag_name)
    new_tag.attrs = tag.attrs.copy()
    tag.wrap(new_tag)
    tag.unwrap()
    return new_tag


def _extr_xmltext(i_path: str, port: str='8070') -> str:
    CFG = dict(
        generateIDs=False,
        consolidate_header=False,
        consolidate_citations=False,
        include_raw_citations=False,
        include_raw_affiliations=False,
        tei_coordinates=False,
        segment_sentences=False)
    dir_grobid = (Path(__file__).parents[1] / 'external/grobid').resolve()
    proc = subprocess.Popen(['./gradlew', 'run'], cwd=str(dir_grobid))
    while True:
        try:
            client = GrobidClient(f'http://localhost:{port}')
        except:
            sleep(1.)
            continue
        break
    _, _, text = client.process_pdf(
        'processFulltextDocument', str(i_path), **CFG)
    proc.kill()
    if text.startswith('[GENERAL] Could not create temprorary file'):
        raise ValueError('Check permission: ' + text)
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


def _extr_figtab_info(figtabs: Tag) -> pd.DataFrame:
    fig_info = []
    for figtab in figtabs:
        tag = figtab['xml:id']
        head = figtab.find('head').get_text()
        desc = figtab.find('figDesc').get_text()
        if desc.startswith(head):
            desc = desc[len(head):]
        fig_info.append((tag, head, desc))
    return pd.DataFrame(fig_info, columns=['tag', 'head', 'desc'])


def _extr_fig_info(soup: BeautifulSoup) -> pd.DataFrame:
    figures = soup.find_all('figure', {'type': False})
    return _extr_figtab_info(figures)


def _extr_tab_info(soup: BeautifulSoup) -> pd.DataFrame:
    tables = soup.find_all('figure', {'type': 'table'})
    return _extr_figtab_info(tables)


def _extr_table(soup: BeautifulSoup) -> dict:
    def tabletag2block(table: Tag) -> str:
        def tabletag2dataframe(table: Tag):
            rows = table.find_all('row')
            dataframe = []
            for row in rows:
                dataframe.append(
                    [cell.get_text() for cell in row.find_all('cell')])
            return pd.DataFrame(dataframe)
        
        def table2block(table: pd.DataFrame) -> dict:
            def row2child(row: pd.Series) -> List[dict]:
                cells = [_make_simple_rich_text(cell) for cell in row]
                return {'type': 'table_row',
                        'table_row': {'cells': cells}}
            table = table.map(lambda x: '' if x is None else x)
            children = [row2child(row) for _, row in table.iterrows()]
            return {'type': 'table',
                    'table': {'table_width': table.shape[1],
                              'children': children}}

        table = tabletag2dataframe(table)
        return table2block(table)

    tables = soup.find_all('figure', {'type': 'table'})
    blocks = dict()
    for table in tables:
        table_id = table['xml:id']
        table = table.find('table')
        blocks[table_id] = tabletag2block(table)
    return blocks


def _find_ids_insert(elements: List[BeautifulSoup], info: pd.DataFrame
                     ) -> List[int]:
    ids_insert = []
    for _, (tag, _, _) in info.iterrows():
        for idx_insert, element in enumerate(elements):
            if element.find('ref', {'target': f'#{tag}'}): break
        ids_insert.append(idx_insert + 1)
    return ids_insert


def _insert_figtab(elements: List[BeautifulSoup], info: pd.DataFrame
                   ) -> List[dict]:
    info = info.copy()
    info['ids_insert'] = _find_ids_insert(elements, info)
    info = info.sort_values('ids_insert', ascending=False)
    for _, (_, head, desc, idx_insert) in info.iterrows():
        to_insert = BeautifulSoup(f'<p>**{head}** {desc}</p>', 'xml').find('p')
        elements.insert(idx_insert, to_insert)


def _insert_fig(elements: List[BeautifulSoup], fig_info: pd.DataFrame
                ) -> List[dict]:
    return _insert_figtab(elements, fig_info)


def _insert_tab(elements: List[BeautifulSoup], tab_info: pd.DataFrame,
                tables: dict) -> List[dict]:
    _insert_figtab(elements, tab_info)
    info = tab_info.copy()
    info['ids_insert'] = _find_ids_insert(elements, info)
    info = info.sort_values('ids_insert', ascending=False)
    for _, (tag, _, _, idx_insert) in info.iterrows():
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
    children = []
    for element in elements:
        if isinstance(element, dict):
            children.append(element)
            continue
        rich_text = _make_simple_rich_text(element.get_text())
        children.append(_make_paragraph_block(rich_text))
    return children


def pdf2children(i_path: str) -> str:
    soup = BeautifulSoup(_extr_xmltext(i_path), 'xml')

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


if __name__ == '__main__':
    from .page import Page
    children = pdf2children('./test/samplepdfs/sample2.pdf')
    page = Page('d5c90701b59e4c68b4d638bcb9271c4b')
    page.create_page('sample2', children)