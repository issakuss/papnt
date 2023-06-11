from typing import List, Dict
import re


def _extr_authors_asbib(authors: List[Dict] | None) -> str:
    def extr_lastname(name: str):
        PREPOSITIONS = [
            "da", "de", "degli", "del", "della", "des", "de la", "de las",
            "de los", "el", "di", "du", "la", "le", "l'", "van", "van de",
            "van den", "van der", "von", "von dem", "von der", "zu",
            "zu der", 
        ]
        prepositions_ = [prepo.replace(' ', '_') for prepo in PREPOSITIONS]

        for preposition in PREPOSITIONS:
            before = ' ' + preposition + ' '
            after = ' ' + preposition.replace(' ', '_') + ' '
            name = re.sub(r'\b' + re.escape(before) + r'\b', after, name)

        preposition = ''
        for preposit_ in prepositions_:
            preposit_ = ' ' + preposit_ + ' '
            match = re.search(preposit_, name)
            if match:
                preposition = match.group(0).replace('_', ' ')[1:]  # remove head space
        return preposition + name.split()[-1]

    if authors is None:
        return ''
    names = []
    for author in authors:
        name = author['name']
        lastname = extr_lastname(name)
        firstnames = name.replace(lastname, '').rstrip()
        lastname = lastname.replace('_', ' ')
        if ' ' in lastname:
            lastname = '{' + lastname + '}'
        if firstnames:
            names.append(f'{lastname}, {firstnames}')
        else:
            names.append(lastname)
    return ' and '.join(names)


def _extr_propvalue(prop: Dict, proptype: str) -> str:
    if (prop[proptype] is None) or (prop[proptype] in [[], '']):
        return None

    match proptype:
        case 'select':
            value = prop['select']['name']
            return value.replace('__', ',')  # Select property allow no commas
        case 'rich_text':
            return prop['rich_text'][-1]['plain_text']
        case 'number':
            return str(prop['number'])
        case 'multi_select':
            return prop['multi_select']
        case _:
            raise ValueError


def notionprop_to_entry(notionprop: Dict, propname_to_bibname: Dict
                        ) -> List:
    props = {propname_to_bibname.get(key) or key: val 
             for key, val in notionprop.items()}
    entry = dict(  # These key names are defined by bib
        ENTRYTYPE = _extr_propvalue(props['entrytype'], 'select'),
        ID = _extr_propvalue(props['id'], 'rich_text'),
        author = _extr_authors_asbib(
            _extr_propvalue(props['author'], 'multi_select')),
        title = _extr_propvalue(props['title'], 'rich_text'),
        edition = _extr_propvalue(props['edition'], 'rich_text'),
        journal = _extr_propvalue(props['journal'], 'select'),
        year = _extr_propvalue(props['year'], 'number'),
        volume = _extr_propvalue(props['volume'], 'rich_text'),
        pages = _extr_propvalue(props['pages'], 'rich_text'),
        doi = _extr_propvalue(props['doi'], 'rich_text'),
        publisher = _extr_propvalue(props['publisher'], 'select'),
        howpublished = _extr_propvalue(props['howpublished'], 'rich_text'),
    )
    return {key: val for key, val in entry.items() if val is not None}