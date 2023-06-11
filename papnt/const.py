SKIPWORDS = (
    'a', 'ab', 'aboard', 'about', 'above', 'across', 'after', 'against', 'al', 'along', 'amid', 'among', 'an', 'and', 'anti', 'around', 'as', 'at', 'before', 'behind', 'below', 'beneath', 'beside', 'besides',
    'between', 'beyond', 'but', 'by',
    'd', 'da', 'das', 'de', 'del', 'dell', 'dello', 'dei', 'degli', 'della', 'dell', 'delle', 'dem', 'den', 'der', 'des', 'despite', 'die', 'do', 'down', 'du', 'during',
    'ein', 'eine', 'einem', 'einen', 'einer', 'eines', 'el', 'en', 'et', 'except',
    'for', 'from',
    'gli',
    'i', 'il', 'in', 'inside', 'into', 'is',
    'l', 'la', 'las', 'le', 'les', 'like', 'lo', 'los',
    'near', 'nor',
    'of', 'off', 'on', 'onto', 'or', 'over',
    'past', 'per', 'plus',
    'round',
    'save', 'since', 'so', 'some', 'sur',
    'than', 'the', 'through', 'to', 'toward', 'towards',
    'un', 'una', 'unas', 'under', 'underneath', 'une', 'unlike', 'uno', 'unos', 'until', 'up', 'upon',
    'versus', 'via', 'von',
    'while', 'with', 'within', 'without',
    'yet',
    'zu', 'zum')

CROSSREF_TO_BIB = {
    # https://ja.wikipedia.org/wiki/BibTeX
    # https://api.crossref.org/v1/types 
    'journal-article': 'article',
    'monograph': 'book',
    'book': 'book',
    'book-section': 'inbook',
    'book-track': 'inbook',
    'book-part': 'inbook',
    'book-chapter': 'inbook',
    'proceedings-article': 'inproceedings',
}