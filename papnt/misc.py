from pathlib import Path
import configparser


def load_config(ini_path: str) -> dict:
    def eachsection(parser, section):
        config = dict(parser.items(section))
        for key in config:
            try:
                config[key] = eval(config[key])
            except:
                pass
        return config
    if not Path(ini_path).exists():
        raise FileNotFoundError(f'Not found: {ini_path}')
    parser = configparser.ConfigParser()
    parser.read(ini_path)
    return {section: eachsection(parser, section)
            for section in parser.sections()}


class FailLogger:
    def __init__(self):
        self.no_doi_extracted = []
        self.no_doi_info = []

    def set_path(self, pdf_path: str | Path):
        self.pdf_path = pdf_path

    def log_no_doi_extracted(self):
        print('DOI could not be extracted from PDF: {self.pdf_path.name}')
        self.no_doi_extracted.append(self.pdf_path.name)

    def log_no_doi_info(self, doi: str):
        print('No information on found DOI: {self.pdf_path.name} ({doi})')
        self.no_doi_info.append((self.pdf_path.name, doi))

    def export_to_text(self):
        with open('skipped-files.txt', 'w') as f:

            f.write('# DOI cannot be extracted:\n')
            for filename in self.no_doi_extracted:
                f.write(f"{filename}\n")

            f.write('\n# No information on found DOI\n')
            for filename, doi in self.no_doi_info:
                f.write(f"{filename}\n")
                if doi:
                    f.write(f"https://doi.org/{doi}\n")
