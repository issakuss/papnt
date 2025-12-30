from typing import Optional
from pathlib import Path

from pdf2doi import pdf2doi


def pdf_to_doi(load_path_pdf: Path | str) -> Optional[str]:
    try:
        return pdf2doi(str(load_path_pdf))['identifier']
    except TypeError:
        return None


if __name__ == '__main__':
    print(pdf_to_doi('samplepdfs/sample3.pdf'))
