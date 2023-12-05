from typing import List
import re

import numpy as np
import pandas as pd

from grobid_client.grobid_client import GrobidClient


TEIURL = r'http://www.tei-c.org/ns/1.0'


def _extr_enclosed(text: str, left: str, right: str) -> List[str]:
    pattern = rf'{left}(.+?){right}'
    found = re.findall(pattern, text, re.DOTALL)
    found = [re.sub(rf'{left}', '', item) for item in found]
    found = [re.sub(rf'{right}', '', item) for item in found]
    return found


def _extr_xmltext(i_path: str, port: str='8070') -> str:
    client = GrobidClient(f'http://localhost:{port}')
    # client.process("processFulltextDocument", "./test/samplepdfs/", output="./test_out/", consolidate_citations=True, tei_coordinates=True, force=True, verbose=True)
    CFG = dict(
        generateIDs=False,
        consolidate_header=False,
        consolidate_citations=False,
        include_raw_citations=False,
        include_raw_affiliations=False,
        tei_coordinates=False,
        segment_sentences=False)
    _, _, text = client.process_pdf('processFulltextDocument', i_path, **CFG)
    return text


def _extr_body(xmltext: str) -> List[str]:
    return _extr_enclosed(
        xmltext, rf'<div\s+xmlns="{TEIURL}">', rf'</div>')


def _strip_text(text: str, newline: List[str], head1: List[str], rm: List[str]
               ) -> str:

    text = re.sub(rf'{"|".join(newline)}', '\n\n', text)
    text = re.sub(rf'{"|".join(head1)}', '# ', text)
    text = re.sub(rf'{"|".join(rm)}', '', text)
    return text


def _strip_body(text: str) -> str:
    return _strip_text(
        text, newline=['<p>'], head1=['<head>'], rm=[
            '</head>', '</p>', '</ref>', r'<ref\s+type="bibr".*?>',
            r'<ref\s+type="formula".*?>', r'<ref\s+type="table".*?>',
            r'<ref\s+type="figure".*?>',
        ])


def _extr_figtab(xmltext: str, left: str, right: str) -> pd.DataFrame:
    text_list = _extr_enclosed(xmltext, rf'{left}', rf'{right}')

    descs = []
    for text in text_list:
        desc = _extr_enclosed(text, rf'<figDesc>', rf'</figDesc>')
        if len(desc) == 0:
            continue
        head = _extr_enclosed(text, rf'<head>', rf'</head>')
        head = head[0] if head else ''
        tag = _extr_enclosed(text, '"', '"')[0]
        descs.append((tag, head, desc[0]))

    return pd.DataFrame(descs, columns=['tag', 'head', 'desc'])


def _extr_figure(xmltext: str) -> pd.DataFrame:
    return _extr_figtab(
        xmltext, rf'<figure\s+xmlns="{TEIURL}"\s+xml:id', r'</figure>')


def _extr_table(xmltext: str) -> pd.DataFrame:
    return _extr_figtab(
        xmltext, rf'<figure\s+xmlns="{TEIURL}"\s+type="table"\s+xml:id=',
        r'</figure>')


def _insert_fig(textlist: List[str], figtext: pd.DataFrame) -> List[str]:
    for _, (tag, head, desc) in figtext.iterrows():
        idx_insert = np.where([tag in text for text in textlist])[0]
        idx_insert = -1 if len(idx_insert) == 0 else idx_insert[0] + 1
        inserted = f'**{head}** {desc}'
        textlist = np.insert(np.array(textlist), idx_insert, inserted)
    return textlist.tolist()


def _insert_tab(textlist: List[str], tabtext: pd.DataFrame) -> List[str]:
    if len(tabtext) == 0:
        return textlist
    for _, (tag, head, desc) in list(tabtext.iterrows())[::-1]:
        idx_insert = np.where([tag in text for text in textlist])[0][0] + 1
        inserted = f'**{head}** {desc}'
        textlist = np.insert(np.array(textlist), idx_insert, inserted)
    return textlist.tolist()


def pdf2text(i_path: str) -> str:
    xmltext = _extr_xmltext(i_path)
    figtext = _extr_figure(xmltext)
    tabtext = _extr_table(xmltext)

    bodytext_list = _extr_body(xmltext)
    bodytext_list = _insert_fig(bodytext_list, figtext)
    bodytext_list = _insert_tab(bodytext_list, tabtext)

    return _strip_body('\n\n'.join(bodytext_list))


if __name__ == '__main__':
    text = pdf2text('./test/samplepdfs/sample1.pdf')
    with open('outputtest.md', 'w') as f:
        f.write(text)