import requests
from pathlib import Path

from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

from .database import Database
from .abbrlister import AbbrLister
from .pdf2doi import pdf_to_doi
from .notionprop import NotionPropMaker
from .prop2entry import notionprop_to_entry


DEBUGMODE = False

# This function is modified
def add_records_from_local_pdfpath(
        database: Database, propnames: dict, input_pdfpath: str):
    path = Path(input_pdfpath)
    no_doi_files = []  # List for not to find DOI

    # If path is a directory, get all PDFs
    if path.is_dir():
        pdf_paths = list(path.glob('**/*.pdf'))  # Get all PDFs under the specified directory
    # If path is a file, add the PDF file to the list
    elif path.is_file() and path.suffix == '.pdf':
        pdf_paths = [path]
    else:
        raise ValueError(f"Invalid path provided: {input_pdfpath}. Please specify a directory or a PDF file.")

    skipped_no_doi = []  # List for not to extract DOI
    skipped_failed_record = []  # List for not to record to notion

    for pdf_path in pdf_paths:
        try:
            doi = pdf_to_doi(pdf_path)
            if doi is None:
                print(f"DOI could not be extracted from PDF: {pdf_path}. Skipping this file.")
                skipped_no_doi.append(pdf_path.name)
                continue  # Skip processing if DOI cannot be extracted

            prop = NotionPropMaker().from_doi(doi, propnames)
            prop |= {'info': {'checkbox': True}}
            database.create(prop)
            print(f"Record created for PDF: {pdf_path}")

        except Exception as e:
            print(f"Error processing {pdf_path}: {e}")
            skipped_failed_record.append((pdf_path.name, doi))

    # Output TXT about not found PDFs
    with open("skipping files list.txt", "w") as f:

        f.write("# PDF can not extracted DOI\n")
        for filename in skipped_no_doi:
            f.write(f"{filename}\n")

        f.write("\n# PDF can not recorded\n")
        for filename, doi in skipped_failed_record:
            f.write(f"{filename}\n")
            if doi:
                f.write(f"https://doi.org/{doi}\n")


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
        PATH_TEMP_PDF.unlink()
        if doi is None:
            continue
        _update_record_from_doi(database, doi, record['id'], propnames)


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
