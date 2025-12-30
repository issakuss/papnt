import unittest
from unittest.mock import patch, MagicMock
import shutil
from tempfile import mkdtemp
from pathlib import Path
import tomllib

from click.testing import CliRunner

from papnt.cli import main
from papnt.database import NotionDatabase
from papnt.notionprop import to_notionprop


class TestPapntCLI(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.ot_dir_test = Path(mkdtemp())
        self.in_path_config_test = self.ot_dir_test / 'config.toml'
        IN_PATH_CONFIG = Path('PRIVATE/config_for_test.toml')
        with open(IN_PATH_CONFIG, 'rb') as f:
            config = tomllib.load(f)
        self.tokenkey = config['database']['tokenkey']
        self.database_id = config['database']['database_id']

    def tearDown(self):
        shutil.rmtree(self.ot_dir_test)

    def test_main(self):
        with patch('papnt.misc.IN_PATH_CONFIG', self.in_path_config_test):
            result = self.runner.invoke(main, catch_exceptions=False)
            self.assertEqual(result.exit_code, 0)

    def test_paths(self):
        with patch('papnt.cli.IN_PATH_CONFIG', self.in_path_config_test), \
             patch('papnt.misc.IN_PATH_CONFIG', self.in_path_config_test):

            IN_DIR_TESTPDF = Path('tests/testdata')
            in_paths = [str(in_path) for in_path in IN_DIR_TESTPDF.glob('*.pdf')]
            result = self.runner.invoke(
                main, ['paths'] + in_paths,
                input=f'{self.tokenkey}\n{self.database_id}',
                catch_exceptions=False)
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

    def test_doi(self):
        database = NotionDatabase(self.tokenkey, self.database_id)
        with open('tests/testdata/doi-list-to-test', 'r') as f:
            for doi in f.readlines():
                database.create({'DOI':
                    {'rich_text': [{'text': {'content': doi.rstrip('\n')}}]}})
        with patch('papnt.cli.IN_PATH_CONFIG', self.in_path_config_test), \
             patch('papnt.misc.IN_PATH_CONFIG', self.in_path_config_test):

            result = self.runner.invoke(
                main, ['doi'], catch_exceptions=False,
                input=f'{self.tokenkey}\n{self.database_id}')
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

    def test_pdf(self):
        print('Manually upload test PDFs to Notion before running this test')
        with patch('papnt.cli.IN_PATH_CONFIG', self.in_path_config_test), \
             patch('papnt.misc.IN_PATH_CONFIG', self.in_path_config_test):

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
                database.create({
                    'DOI': to_notionprop(doi.rstrip('\n'), 'rich_text'),
                    'Cite in': to_notionprop(['test'], 'multi_select')})
        with patch('papnt.cli.IN_PATH_CONFIG', self.in_path_config_test), \
             patch('papnt.misc.IN_PATH_CONFIG', self.in_path_config_test):

            # paths command
            IN_DIR_TESTPDF = Path('tests/testdata')
            in_paths = [str(in_path)
                        for in_path in IN_DIR_TESTPDF.glob('*.pdf')]
            result = self.runner.invoke(
                main, ['paths'] + in_paths[0:2],
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
        with patch('papnt.cli.IN_PATH_CONFIG', self.in_path_config_test), \
             patch('papnt.misc.IN_PATH_CONFIG', self.in_path_config_test):

            IN_DIR_TESTPDF = Path('tests/testdata/fail-to-record')
            in_paths = [str(in_path)
                        for in_path in IN_DIR_TESTPDF.glob('*.pdf')]
            result = self.runner.invoke(
                main, ['paths'] + in_paths,
                input=f'{self.tokenkey}\n{self.database_id}')
            if result.exit_code != 0:
                print(result.exception)
            self.assertEqual(result.exit_code, 0)

if __name__ == '__main__':
    unittest.main()