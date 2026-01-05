import unittest
from unittest.mock import patch
import shutil
from tempfile import mkdtemp
from pathlib import Path
import tomllib

from click.testing import CliRunner

from papnt.misc import load_config, save_config
from papnt.cli import main
from papnt.database import NotionDatabase
from papnt.notionprop import to_notionprop, add_fileupload_prop


TEST_GROBID = False

class TestPapntCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.ot_dir_test = Path(mkdtemp())
        self.load_path_config_test = self.ot_dir_test / 'config.toml'
        LOAD_PATH_CONFIG = Path('PRIVATE/config_for_test.toml')
        with open(LOAD_PATH_CONFIG, 'rb') as f:
            config = tomllib.load(f)
        self.tokenkey = config['database']['tokenkey']
        self.database_id = config['database']['database_id']
        self.grobidserver = config['grobid']['server']

    def tearDown(self):
        shutil.rmtree(self.ot_dir_test)

    def test_main(self):
        with patch('papnt.misc.LOAD_PATH_CONFIG', self.load_path_config_test):
            result = self.runner.invoke(main, catch_exceptions=False)
            self.assertEqual(result.exit_code, 0)

    def test_paths_grobid(self):
        with patch('papnt.cli.LOAD_PATH_CONFIG', self.load_path_config_test), \
             patch('papnt.misc.LOAD_PATH_CONFIG', self.load_path_config_test):

            config = load_config()
            config['grobid']['server'] = self.grobidserver
            save_config(config)

            LOAD_PATH = 'tests/testdata/elsevier.pdf'
            result = self.runner.invoke(
                main, ['paths'] + [LOAD_PATH],
                input=f'{self.tokenkey}\n{self.database_id}',
                catch_exceptions=False)
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

    def test_paths_single_pdf(self):
        with patch('papnt.cli.LOAD_PATH_CONFIG', self.load_path_config_test), \
             patch('papnt.misc.LOAD_PATH_CONFIG', self.load_path_config_test):

            LOAD_PATH = 'tests/testdata/elsevier.pdf'
            result = self.runner.invoke(
                main, ['paths'] + [LOAD_PATH],
                input=f'{self.tokenkey}\n{self.database_id}',
                catch_exceptions=False)
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

    def test_paths_multi_pdf(self):
        with patch('papnt.cli.LOAD_PATH_CONFIG', self.load_path_config_test), \
             patch('papnt.misc.LOAD_PATH_CONFIG', self.load_path_config_test):

            if TEST_GROBID:
                config = load_config()
                config['grobid']['server'] = self.grobidserver
                save_config(config)

            IN_DIR_TESTPDF = Path('tests/testdata')
            load_paths = [str(LOAD_PATH)
                          for LOAD_PATH in IN_DIR_TESTPDF.glob('*.pdf')]
            result = self.runner.invoke(
                main, ['paths'] + load_paths,
                input=f'{self.tokenkey}\n{self.database_id}',
                catch_exceptions=False)
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

    def test_paths_dir(self):
        with patch('papnt.cli.LOAD_PATH_CONFIG', self.load_path_config_test), \
             patch('papnt.misc.LOAD_PATH_CONFIG', self.load_path_config_test):

            IN_DIR_TESTPDF = 'tests/testdata'
            result = self.runner.invoke(
                main, ['paths'] + [IN_DIR_TESTPDF],
                input=f'{self.tokenkey}\n{self.database_id}')
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

    def test_doi(self):
        database = NotionDatabase(self.tokenkey, self.database_id)
        with open('tests/testdata/doi-list-to-test', 'r') as f:
            for doi in f.readlines():
                prop = {'DOI': to_notionprop(doi.rstrip('\n'), 'rich_text'),
                        'Name': to_notionprop('', 'title')}
                database.create(prop, check_info=False)
        with patch('papnt.cli.LOAD_PATH_CONFIG', self.load_path_config_test), \
             patch('papnt.misc.LOAD_PATH_CONFIG', self.load_path_config_test):

            result = self.runner.invoke(
                main, ['doi'], catch_exceptions=False,
                input=f'{self.tokenkey}\n{self.database_id}')
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

    def test_pdf(self):
        database = NotionDatabase(self.tokenkey, self.database_id)
        load_paths = [LOAD_PATH
                      for LOAD_PATH in Path('tests/testdata').glob('*.pdf')]
        for load_path in load_paths:
            prop = add_fileupload_prop(
                {'Name': to_notionprop(load_path.name, 'title')},
                load_path, database.notion, 'PDF')
            database.create(prop, check_info=False)

        with patch('papnt.cli.LOAD_PATH_CONFIG', self.load_path_config_test), \
             patch('papnt.misc.LOAD_PATH_CONFIG', self.load_path_config_test):

            if TEST_GROBID:
                config = load_config()
                config['grobid']['server'] = self.grobidserver
                save_config(config)

            result = self.runner.invoke(
                main, ['pdf'],
                input=f'{self.tokenkey}\n{self.database_id}',
                catch_exceptions=False)
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

    def test_makebib(self):
        database = NotionDatabase(self.tokenkey, self.database_id)
        with open('tests/testdata/doi-list-to-test', 'r') as f:
            for doi in f.readlines():
                prop = {'DOI': to_notionprop(doi.rstrip('\n'), 'rich_text'),
                        'Cite in': to_notionprop(['test'], 'multi_select')}
                database.create(prop, check_info=False)
        with patch('papnt.cli.LOAD_PATH_CONFIG', self.load_path_config_test), \
             patch('papnt.misc.LOAD_PATH_CONFIG', self.load_path_config_test):

            # paths command (test input tokenkey and database ID first)
            IN_DIR_TESTPDF = Path('tests/testdata')
            LOAD_PATHS = [str(LOAD_PATH)
                          for LOAD_PATH in IN_DIR_TESTPDF.glob('*.pdf')]
            result = self.runner.invoke(
                main, ['paths'] + LOAD_PATHS[0:1],
                input=f'{self.tokenkey}\n{self.database_id}',
                catch_exceptions=False)
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

            # doi command
            result = self.runner.invoke(
                main, ['doi'], catch_exceptions=False)
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

            # makebib command
            result = self.runner.invoke(
                main, ['makebib', 'test'],
                input=str(Path.home() / 'Desktop'),
                catch_exceptions=False)
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

    def test_fail_paths(self):
        with patch('papnt.cli.LOAD_PATH_CONFIG', self.load_path_config_test), \
             patch('papnt.misc.LOAD_PATH_CONFIG', self.load_path_config_test):

            IN_DIR_TESTPDF = Path('tests/testdata/fail-to-record')
            LOAD_PATHs = [str(LOAD_PATH)
                        for LOAD_PATH in IN_DIR_TESTPDF.glob('*.pdf')]
            result = self.runner.invoke(
                main, ['paths'] + LOAD_PATHs,
                input=f'{self.tokenkey}\n{self.database_id}')
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

if __name__ == '__main__':
    unittest.main()
