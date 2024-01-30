import requests
import subprocess
from pathlib import Path
from shutil import unpack_archive, rmtree


DIR_EXTERNAL = Path(__file__).parent / 'external'


def download_grobid(version: str):
    O_PATH_ZIP = DIR_EXTERNAL / 'grobid.zip'
    URL = f'https://github.com/kermitt2/grobid/archive/{version}.zip'
    print(f'Downloading Grobid {version}...')
    data = requests.get(URL).content
    O_PATH_ZIP.parent.mkdir(exist_ok=True, parents=True)
    with O_PATH_ZIP.open('wb') as f:
        f.write(data)
    print('...complete.')


def unzip_grobid(version: str):
    I_PATH_ZIP = DIR_EXTERNAL / 'grobid.zip'
    O_PATH_UNZIP = DIR_EXTERNAL / 'grobid'
    O_PATH = DIR_EXTERNAL / 'grobid'
    TEMP_DIR = DIR_EXTERNAL / 'temp'

    if O_PATH.exists():
        rmtree(O_PATH)
    unpack_archive(I_PATH_ZIP, O_PATH_UNZIP)
    O_PATH.rename(TEMP_DIR)
    (TEMP_DIR / f'grobid-{version}').rename(O_PATH)
    I_PATH_ZIP.unlink()
    TEMP_DIR.rmdir()
    
    for filepath in O_PATH.glob('*'):
        filepath.chmod(0o777)


def check_grobid_run():
    (DIR_EXTERNAL / 'grobid/gradlew').chmod(0o777)
    result = subprocess.run(
        ['./gradlew', 'run'], cwd=str(DIR_EXTERNAL / 'grobid'),
        stdout=subprocess.PIPE, text=True)
    print(result.stdout)


if __name__ == '__main__':
    # install_grobid()
    download_grobid('0.8.0')
    unzip_grobid('0.8.0')
    check_grobid_run()