from pathlib import Path
import unittest

from papnt.misc import load_config
from papnt.database import Database, DatabaseInfo
from papnt.mainfunc import (
    add_records_from_local_pdfpath,
    update_unchecked_records_from_doi,
    update_unchecked_records_from_uploadedpdf,
    make_bibfile_from_records,
    make_abbrjson_from_bibpath,
)

config = load_config('papnt/config.ini')
database = Database(DatabaseInfo())


class Test(unittest.TestCase):
    def paths(self):
        I_DIR_TESTPDF = Path('tests/testdata')
        for i_path in I_DIR_TESTPDF.glob('*.pdf'):
            add_records_from_local_pdfpath(
                database, config['propnames'], i_path)
        add_records_from_local_pdfpath(
            database, config['propnames'], I_DIR_TESTPDF)

    def doi(self):
        for doi in open('tests/testdata/doi-list-to-test', 'r').readlines():
            database.create({'DOI':
                {'rich_text': [{'text': {'content': doi.rstrip('\n')}}]}})
        update_unchecked_records_from_doi(database, config['propnames'])

    def pdf(self):
        update_unchecked_records_from_uploadedpdf(
            database, config['propnames'])

    def makebib(self):
        target = 'test'
        make_bibfile_from_records(
            database, target, config['propnames'],
            config['misc']['dir_save_bib'])
        make_abbrjson_from_bibpath(
            f'{config["misc"]["dir_save_bib"]}/{target}.bib',
            config['abbr'])


if __name__ == '__main__':
    Test().paths()
    Test().doi()
    Test().pdf()
    input('Set "test" in "Cite in" of any record manually, and press key to continue...')
    Test().makebib()
