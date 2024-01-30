import requests
from pathlib import Path

from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

from .database import Database
from .abbrlister import AbbrLister
from .pdf2doi import pdf_to_doi
from .notionprop import NotionPropMaker
from .prop2entry import notionprop_to_entry
from .install import download_grobid, unzip_grobid
from .page import Page
from .pdf2text  import pdf2children


DEBUGMODE = False
PATH_TEMP_PDF = Path('you-can-delete-this-file.pdf')


def add_records_from_local_pdfpath(
        database: Database, propnames: dict, input_pdfpath: str,
        run_ocr: bool):

    doi = pdf_to_doi(input_pdfpath)
    if doi is None:
        raise Exception('DOI was not extracted from PDF.')
    prop = NotionPropMaker().from_doi(doi, propnames)
    prop |= {'info': {'checkbox': True}}
    database.create(prop)

    if run_ocr:
        page = Page(database.fetch_newest_record()['results'][0]['id'])
        pagename = f'Fulltext-{prop["Name"]["title"][0]["text"]["content"]}'
        page.create_page(pagename, pdf2children(input_pdfpath))


def _update_record_from_doi(
        database: Database, doi: str, id_record: str, propnames: dict):

    prop_maker = NotionPropMaker()
    prop = prop_maker.from_doi(doi, propnames)
    prop |= {'info': {'checkbox': True}}
    try:
        database.update(id_record, prop)
    except Exception as e:
        print(str(e))
        name = prop['Name']['title'][0]['text']['content']
        raise ValueError(f'Error while updating record: {name}')


def _fetch_pdf(fileurl: Path, o_path: Path):
    pdffile = requests.get(fileurl).content
    with o_path.open(mode='wb') as f:
        f.write(pdffile)


def _create_fulltext_from_record(record: dict, pdfpropname: str):
    pagename = record["properties"]["Name"]["title"][0]["plain_text"]
    pagename = f'Fulltext-{pagename}'
    fileurl = record['properties'][pdfpropname]['files']
    if len(fileurl) == 0:
        return
    fileurl = fileurl[0]['file']['url']
    _fetch_pdf(fileurl, PATH_TEMP_PDF)
    page = Page(record['id'])
    page.create_page(pagename, pdf2children(PATH_TEMP_PDF))
    PATH_TEMP_PDF.unlink()


def update_unchecked_records_from_doi(database: Database, propnames: dict,
                                      run_ocr: bool):
    filter = {
        'and': [{'property': 'info', 'checkbox': {'equals': False}},
                {'property': 'DOI', 'rich_text': {'is_not_empty': True}}]}
    for record in database.fetch_records(filter).db_results:
        doi = record['properties']['DOI']['rich_text'][0]['plain_text']
        _update_record_from_doi(database, doi, record['id'], propnames)
        if run_ocr:
            _create_fulltext_from_record(record, propnames['pdf'])


def update_unchecked_records_from_uploadedpdf(
        database: Database, propnames: dict, run_ocr: bool):
    filter = {
        'and': [{'property': 'info', 'checkbox': {'equals': False}},
                {'property': propnames['pdf'],
                 'files': {'is_not_empty': True}}]}
    for record in database.fetch_records(filter).db_results:
        fileurl = record['properties'][propnames['pdf']]
        fileurl = fileurl['files'][0]['file']['url'] 
        _fetch_pdf(fileurl, PATH_TEMP_PDF)
        doi = pdf_to_doi(PATH_TEMP_PDF)
        PATH_TEMP_PDF.unlink()
        if doi is None:
            continue
        _update_record_from_doi(database, doi, record['id'], propnames)
        if run_ocr:
            _create_fulltext_from_record(record, propnames['pdf'])


def make_bibfile_from_records(database: Database, target: str,
                              propnames: dict, dir_save_bib: str):
    propname_to_bibname = {val: key for key, val in propnames.items()}
    filter = {'property': propnames['output_target'],
              'multi_select': {'contains': target}}
    entries = [notionprop_to_entry(record['properties'], propname_to_bibname)
               for record in database.fetch_records(filter).db_results]

    bib_db = BibDatabase()
    bib_db.entries = entries
    writer = BibTexWriter()
    with open(f'{dir_save_bib}/{target}.bib', 'w') as bibfile:
        bibfile.write(writer.write(bib_db))


def make_abbrjson_from_bibpath(input_bibpath: str, special_abbr: dict):
    lister = AbbrLister(input_bibpath)
    lister.listup(special_abbr).save(input_bibpath.replace('.bib', '.json'))


def install_grobid(version: str):
    download_grobid(version)
    unzip_grobid(version)


def add_fulltext_from_pdf_on_notion_url(pdfprop: str, url: str):
    record_id = url.split('/')[-1].split('-')[-1].split('?')[0]
    record = Page(record_id).notion.pages.retrieve(record_id)
    _create_fulltext_from_record(record, pdfprop)


if __name__ == '__main__':
    from .misc import load_config
    from .database import DatabaseInfo

    config = load_config(Path(__file__).parent / 'config.ini')
    database = Database(DatabaseInfo())

    add_fulltext_from_pdf_on_notion_url(
        config['propnames']['pdf'],
        'https://www.notion.so/issakuss/Glasser2016-0f4a53d07c3243d2aa67cd773314119e?pvs=4')
    ocrrun = config['fulltext']['autorun']
    add_records_from_local_pdfpath(
        database, config['propnames'], 'test/samplepdfs/sample1.pdf', ocrrun)
    update_unchecked_records_from_doi(database, config['propnames'], ocrrun)
    update_unchecked_records_from_uploadedpdf(
        database, config['propnames'], ocrrun)
    make_bibfile_from_records(
        database, 'test', config['propnames'], config['misc']['dir_save_bib'])
    make_abbrjson_from_bibpath(
        config['misc']['dir_save_bib'] + 'test.bib', config['abbr'])
