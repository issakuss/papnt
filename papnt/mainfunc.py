import requests
from pathlib import Path

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
converter = PDF2ChildrenConverter(
    load_config()['grobid']['server'])


def add_records_from_local_pdfpath(
        database: NotionDatabase, propnames: dict, input_pdfpath: str | Path):

    input_pdfpath = Path(input_pdfpath)
    if input_pdfpath.is_dir():
        pdf_paths = list(input_pdfpath.glob('**/*.pdf'))
    elif input_pdfpath.is_file() and input_pdfpath.suffix == '.pdf':
        pdf_paths = [input_pdfpath]
    else:
        raise RuntimeError(f'Invalid path provided: {input_pdfpath}. '
                          'Please specify a directory or a PDF file.')

    logger = FailLogger()
    for pdf_path in pdf_paths:
        logger.set_path(pdf_path)
        doi = pdf_to_doi(pdf_path) or logger.log_no_doi_extracted()
        if doi is None:
            continue
        try:
            prop = NotionPropMaker().from_doi(doi, propnames) | \
                   {'info': {'checkbox': True}}
        except Exception as e:
            logger.log_no_doi_info(doi)
            prop = {'Name': to_notionprop(pdf_path.name, 'title')}
        prop = add_fileupload_prop(
            prop, pdf_path, database.notion, propnames['pdf'])
        created_page_id = database.create(prop)['id']
        children = converter.convert(pdf_path)
        database.add_children(created_page_id, children, blocktype='toggle',
                              title='Text extracted by GROBID')
        print(f'Recorded: {pdf_path}')

    shallowest_pdf = min(pdf_paths, key=lambda p: len(p.parts))
    logger.export_to_text(shallowest_pdf.parent)


def _update_record_from_doi(
        database: NotionDatabase, doi: str, id_record: str, propnames: dict):

    prop_maker = NotionPropMaker()
    try:
        prop = prop_maker.from_doi(doi, propnames)
        prop |= {'info': {'checkbox': True}}
        database.update_properties(id_record, prop)
        for note in prop_maker.notes:
            database.add_children(id_record, note, 'paragraph')

    except Exception as e:
        print(str(e))
        raise RuntimeError(f'Error while updating record: {doi}')


def update_unchecked_records_from_doi(database: NotionDatabase, propnames: dict):
    filter = {
        'and': [{'property': 'info', 'checkbox': {'equals': False}},
                {'property': 'DOI', 'rich_text': {'is_not_empty': True}}]}
    for record in database.fetch_records(filter).db_results:
        doi = record['properties']['DOI']['rich_text'][0]['plain_text']
        _update_record_from_doi(database, doi, record['id'], propnames)


def update_unchecked_records_from_uploadedpdf(
        database: NotionDatabase, propnames: dict):
    PATH_TEMP_PDF = Path('you-can-delete-this-file.pdf')
    filter = {
        'and': [{'property': 'info', 'checkbox': {'equals': False}},
                {'property': propnames['pdf'],
                 'files': {'is_not_empty': True}}]}
    for record in database.fetch_records(filter).db_results:
        fileurl = record['properties'][propnames['pdf']]
        fileurl = fileurl['files'][0]['file']['url']
        pdffile = requests.get(fileurl).content
        with PATH_TEMP_PDF.open(mode='wb') as f:
            f.write(pdffile)
        doi = pdf_to_doi(PATH_TEMP_PDF)
        children = converter.convert(PATH_TEMP_PDF)
        database.add_children(record['id'], children, blocktype='toggle',
                              title='Text extracted by GROBID')
        PATH_TEMP_PDF.unlink()
        if doi is None:
            continue
        try:
            _update_record_from_doi(database, doi, record['id'], propnames)
        except RuntimeError as e:
            print(e)
            continue


def make_bibfile_from_records(database: NotionDatabase, target: str,
                              propnames: dict, out_path_bib: str):
    propname_to_bibname = {val: key for key, val in propnames.items()}
    filter = {'property': propnames['output_target'],
              'multi_select': {'contains': target}}
    entries = [notionprop_to_entry(record['properties'], propname_to_bibname)
               for record in database.fetch_records(filter).db_results]

    bib_db = BibDatabase()
    bib_db.entries = entries
    writer = BibTexWriter()
    open(out_path_bib, 'w', encoding='UTF-8').write(writer.write(bib_db))


def make_abbrjson_from_bibpath(input_bibpath: Path, special_abbr: dict):
    lister = AbbrLister(input_bibpath)
    lister.listup(special_abbr).save(input_bibpath.with_suffix('.json'))


if __name__ == '__main__':
    from .misc import load_config
    from .database import DatabaseInfo

    config = load_config(Path(__file__).parent / 'config.ini')
    database = NotionDatabase(DatabaseInfo())

    add_records_from_local_pdfpath(
        database, config['propnames'], 'tests/testdata/fail-to-record/x-plosone.pdf')
        # database, config['propnames'], 'tests/testdata/elsevier.pdf')