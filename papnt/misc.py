from pathlib import Path
import tomllib

import tomli_w


LOAD_PATH_CONFIG = Path.home() / '.config/papnt/config.toml'


def make_config_file_from_template() -> None:
    if LOAD_PATH_CONFIG.exists():
        return
    load_path_template = Path(__file__).parent / 'config_template.toml'
    LOAD_PATH_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    with open(load_path_template, 'rb') as f_src:
        with open(LOAD_PATH_CONFIG, 'wb') as f_dst:
            f_dst.write(f_src.read())


def load_config() -> dict:
    if not LOAD_PATH_CONFIG.exists():
        make_config_file_from_template()
    with open(LOAD_PATH_CONFIG, 'rb') as f:
        return tomllib.load(f)


def save_config(config_data: dict) -> None:
    with open(LOAD_PATH_CONFIG, 'wb') as f:
        tomli_w.dump(config_data, f)


class FailLogger:
    def __init__(self):
        self.no_doi_extracted = []
        self.no_doi_info = []

    def set_path(self, load_path_pdf: str | Path):
        self.load_path_pdf = load_path_pdf

    def log_no_doi_extracted(self):
        print('DOI could not be extracted from PDF: {self.load_path_pdf.name}')
        self.no_doi_extracted.append(self.load_path_pdf.name)

    def log_no_doi_info(self, doi: str):
        print(f'No information on found DOI: {self.load_path_pdf.name} ({doi})')
        self.no_doi_info.append((self.load_path_pdf.name, doi))

    def export_to_text(self, save_path_log: str | Path):
        if not (self.no_doi_extracted or self.no_doi_info):
            return
        with (Path(save_path_log) / 'skipped-files.txt').open('w') as f:
            if self.no_doi_extracted:
                f.write('# DOI cannot be extracted:\n')
                for filename in self.no_doi_extracted:
                    f.write(f"{filename}\n")

            if self.no_doi_info:
                f.write('\n# No information on found DOI\n')
                for filename, doi in self.no_doi_info:
                    f.write(f"{filename}: ")
                    if doi:
                        f.write(f"https://doi.org/{doi}\n")
