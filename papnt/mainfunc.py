import requests
from pathlib import Path

from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

from .misc import load_config, FailLogger
from .database import Database
from .abbrlister import AbbrLister
from .pdf2doi import pdf_to_doi
from .notionprop import NotionPropMaker, to_notionprop
from .prop2entry import notionprop_to_entry
from .pdf2text import PDF2ChildrenConverter


DEBUGMODE = False
converter = PDF2ChildrenConverter(
    load_config(Path(__file__).parent / 'config.ini')['grobid']['server'])


def add_records_from_local_pdfpath(
        database: Database, propnames: dict, input_pdfpath: str | Path):

    input_pdfpath = Path(input_pdfpath)
    if input_pdfpath.is_dir():
        pdf_paths = list(input_pdfpath.glob('**/*.pdf'))
    elif input_pdfpath.is_file() and input_pdfpath.suffix == '.pdf':
        pdf_paths = [input_pdfpath]
    else:
        raise ValueError(f'Invalid path provided: {input_pdfpath}. '
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
            prop = to_notionprop(pdf_path.name, 'title')
        created_page_id = database.create(prop)['id']
        children = converter.convert(pdf_path)
        database.add_children(created_page_id, children, blocktype='toggle',
                              title='Text extracted by GROBID')
        print(f'Recorded: {pdf_path}')

    shallowest_pdf = min(pdf_paths, key=lambda p: len(p.parts))
    logger.export_to_text(shallowest_pdf.parent)


def _update_record_from_doi(
        database: Database, doi: str, id_record: str, propnames: dict):

    prop_maker = NotionPropMaker()
    prop = prop_maker.from_doi(doi, propnames)
    prop |= {'info': {'checkbox': True}}
    try:
        database.update_properties(id_record, prop)
        for note in prop_maker.notes:
            database.add_children(id_record, note, 'paragraph')

    except Exception as e:
        print(str(e))
        name = prop['Name']['title'][0]['text']['content']
        raise ValueError(f'Error while updating record: {name}')


def update_unchecked_records_from_doi(database: Database, propnames: dict):
    filter = {
        'and': [{'property': 'info', 'checkbox': {'equals': False}},
                {'property': 'DOI', 'rich_text': {'is_not_empty': True}}]}
    for record in database.fetch_records(filter).db_results:
        doi = record['properties']['DOI']['rich_text'][0]['plain_text']
        _update_record_from_doi(database, doi, record['id'], propnames)


def update_unchecked_records_from_uploadedpdf(
        database: Database, propnames: dict):
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
        _update_record_from_doi(database, doi, record['id'], propnames)


def make_bibfile_from_records(database: Database, target: str,
                              propnames: dict, dir_save_bib: str):
    if dir_save_bib == '':
        raise RuntimeError('Edit "dir_save_bib" key in config.ini')

    propname_to_bibname = {val: key for key, val in propnames.items()}
    filter = {'property': propnames['output_target'],
              'multi_select': {'contains': target}}
    entries = [notionprop_to_entry(record['properties'], propname_to_bibname)
               for record in database.fetch_records(filter).db_results]

    bib_db = BibDatabase()
    bib_db.entries = entries
    writer = BibTexWriter()
    output_path = f'{dir_save_bib}/{target}.bib'
    open(output_path, 'w', encoding='UTF-8').write(writer.write(bib_db))


def make_abbrjson_from_bibpath(input_bibpath: str, special_abbr: dict):
    lister = AbbrLister(input_bibpath)
    lister.listup(special_abbr).save(input_bibpath.replace('.bib', '.json'))


if __name__ == '__main__':
    from .misc import load_config
    from .database import DatabaseInfo

    config = load_config(Path(__file__).parent / 'config.ini')
    database = Database(DatabaseInfo())

    add_records_from_local_pdfpath(
        database, config['propnames'], 'test/samplepdfs/sample1.pdf')
    update_unchecked_records_from_doi(database, config['propnames'])
    update_unchecked_records_from_uploadedpdf(
        database, config['propnames'])
    make_bibfile_from_records(
        database, 'test', config['propnames'], config['misc']['dir_save_bib'])
    make_abbrjson_from_bibpath(
        config['misc']['dir_save_bib'] + 'test.bib', config['abbr'])
