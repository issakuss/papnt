import json

from bibtexparser import loads
from bibtexparser.bparser import BibTexParser
from iso4 import abbreviate
import nltk


def _remove_duplicated_space(dict_: dict):
    return {k: v.replace('  ', ' ') for k, v in dict_.items()}


class AbbrLister:
    def __init__(self, path_bib: str):
        with open(path_bib, 'r') as f:
            bibtext = f.read()
        parser = BibTexParser()
        bibdatabase = loads(bibtext, parser).entries_dict
        names_journal = [article.get('journal')
                         for article in bibdatabase.values()]
        self.names_journal = sorted(list(set(
            [name for name in names_journal if name is not None])))

        nltk.download('wordnet')

    def listup(self, spec: dict | None=None):
        """
        sepc: dict
            Can specify abbreviation like...
            {'PLOS ONE': 'PLOS ONE'}
            Case insensitive.
        """
        abbrs = {name: abbreviate(name) for name in self.names_journal}
        self.abbrs = _remove_duplicated_space(abbrs)
        if spec is None:
            return self
        specified_abbrs = {name: spec[name.lower()]
                           for name in self.names_journal
                           if spec.get(name.lower())}
        self.abbrs = self.abbrs | specified_abbrs
        return self

    def save(self, save_path: str):
        if not hasattr(self, 'abbrs'):
            raise ValueError('Use listup() first.')

        with open(save_path, 'w') as f:
            json.dump(
                {'default': {'container-title': self.abbrs}}, f, indent=2)


if __name__ == '__main__':
    lister = AbbrLister('/Users/issakuss/Desktop/study14.bib')
    lister.listup().save('/Users/issakuss/Desktop/study14.json')