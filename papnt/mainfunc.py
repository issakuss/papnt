from typing import Tuple
from pathlib import Path
import requests

from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

from .misc import load_config, FailLogger
from .database import NotionDatabase
from .abbrlister import AbbrLister
from .pdf2doi import pdf_to_doi
from .notionprop import NotionPropMaker, to_notionprop, add_fileupload_prop
from .prop2entry import notionprop_to_entry
from .pdf2text import PDF2ChildrenConverter


DEBUGMODE = False


def add_records_from_local_pdfpath(database: NotionDatabase, propnames: dict,
                                   load_paths_pdf: Tuple[Path, ...]):

    def extract_prop_from_pdf(load_path_pdf: Path, logger: FailLogger) -> dict:
        logger.set_path(load_path_pdf)
        emptyprop = {'Name': to_notionprop(load_path_pdf.name, 'title')}
        doi: str | None = pdf_to_doi(load_path_pdf)
        if doi is None:
            logger.log_no_doi_extracted()
            prop = emptyprop
        try:
            prop = NotionPropMaker().from_doi(doi, propnames)
        except Exception as e:
            logger.log_no_doi_info(doi)
            prop = emptyprop
        return add_fileupload_prop(
            prop, load_path_pdf, database.notion, propnames['pdf'])

    if len(load_paths_pdf) == 1 and load_paths_pdf[0].is_dir():
        load_paths_pdf = tuple(load_paths_pdf[0].glob('*.pdf'))

    converter = PDF2ChildrenConverter(
        load_config()['grobid']['server'])
    logger = FailLogger()
    for load_path_pdf in load_paths_pdf:
        prop = extract_prop_from_pdf(load_path_pdf, logger)
        children = converter.convert(load_path_pdf)
        database.create(prop, children)
        print(f'Recorded: {load_path_pdf}')

    shallowest_pdf = min(load_paths_pdf, key=lambda p: len(p.parts))
    logger.export_to_text(shallowest_pdf.parent)


def _update_record_from_doi(
        database: NotionDatabase, doi: str, id_record: str, propnames: dict):
    try:
        prop = NotionPropMaker().from_doi(doi, propnames)
        database.update_properties(id_record, prop)
    except Exception as e:
        raise RuntimeError(f'Error while updating record: {doi}') from e


def update_unchecked_records_from_doi(database: NotionDatabase, propnames: dict):
    notionfilter = {
        'and': [{'property': 'info', 'checkbox': {'equals': False}},
                {'property': 'DOI', 'rich_text': {'is_not_empty': True}}]}
    for record in database.fetch_records(notionfilter).db_results:
        doi = record['properties']['DOI']['rich_text'][0]['plain_text']
        _update_record_from_doi(database, doi, record['id'], propnames)


def update_unchecked_records_from_uploadedpdf(
        database: NotionDatabase, propnames: dict):

    def download_pdf(save_path_temppdf: Path, record: dict):
        files = record['properties'][propnames['pdf']]['files']
        pdffile = requests.get(files[0]['file']['url']).content
        with save_path_temppdf.open(mode='wb') as f:
            f.write(pdffile)

    SAVE_PATH_TEMPPDF = Path('you-can-delete-this-file.pdf')
    converter = PDF2ChildrenConverter(
        load_config()['grobid']['server'])
    notionfilter = {
        'and': [{'property': 'info', 'checkbox': {'equals': False}},
                {'property': propnames['pdf'],
                 'files': {'is_not_empty': True}}]}
    for record in database.fetch_records(notionfilter).db_results:
        download_pdf(SAVE_PATH_TEMPPDF, record)
        doi = pdf_to_doi(SAVE_PATH_TEMPPDF)
        prop = {'Name': to_notionprop(SAVE_PATH_TEMPPDF.name, 'title')}
        if doi is not None:
            prop = NotionPropMaker().from_doi(doi, propnames)
        children = converter.convert(SAVE_PATH_TEMPPDF)
        database.update_record(record['id'], prop, children)

        SAVE_PATH_TEMPPDF.unlink()


def make_bibfile_from_records(database: NotionDatabase, target: str,
                              propnames: dict, save_path_bib: str):
    propname_to_bibname = {val: key for key, val in propnames.items()}
    notionfilter = {'property': propnames['output_target'],
                    'multi_select': {'contains': target}}
    entries = [notionprop_to_entry(record['properties'], propname_to_bibname)
               for record in database.fetch_records(notionfilter).db_results]

    bib_db = BibDatabase()
    bib_db.entries = entries
    writer = BibTexWriter()
    with open(save_path_bib, 'w', encoding='UTF-8') as f:
        f.write(writer.write(bib_db))


def make_abbrjson_from_bibpath(load_path_bib: Path, special_abbr: dict):
    lister = AbbrLister(load_path_bib)
    save_path_bib = load_path_bib.with_suffix('.json')
    lister.listup(special_abbr).save(save_path_bib)
