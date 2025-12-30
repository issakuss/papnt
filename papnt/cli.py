from pathlib import Path
import click
from click.core import Context

from .misc import load_config, save_config, LOAD_PATH_CONFIG
from .database import NotionDatabase
from .mainfunc import (
    add_records_from_local_pdfpath,
    update_unchecked_records_from_doi,
    update_unchecked_records_from_uploadedpdf,
    make_bibfile_from_records, make_abbrjson_from_bibpath)


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: Context):
    ctx.obj = dict(
        config=load_config(),
    )
    click.echo('Wellcome to Papnt!')
    click.echo(f'Your config file is in: {LOAD_PATH_CONFIG}')
    if ctx.invoked_subcommand is None:
        click.echo('try `papnt --help` for help')

@main.command()
@click.argument(
    'load_paths_pdf', nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.pass_context
def paths(ctx: Context, load_paths_pdf: Path | tuple[Path, ...]):
    """Add record(s) to database by local path to PDF file"""
    if not load_paths_pdf:
        click.echo('Indicate local path(s) of PDF(s)')
        return

    db = _fetch_database(ctx)
    propnames = ctx.obj['config']['propnames']
    add_records_from_local_pdfpath(db, propnames, load_paths_pdf)


@main.command()
@click.pass_context
def doi(ctx: Context):
    """Fill information in record(s) by DOI"""
    update_unchecked_records_from_doi(
        _fetch_database(ctx), ctx.obj['config']['propnames'])


@main.command()
@click.pass_context
def pdf(ctx: Context):
    """Fill information in record(s) by uploaded PDF file"""
    update_unchecked_records_from_uploadedpdf(
        _fetch_database(ctx), ctx.obj['config']['propnames'])


@main.command()
@click.argument('target')
@click.pass_context
def makebib(ctx: Context, target: str):
    """Make BIB file including reference information from database"""
    config = ctx.obj['config']

    save_dir = _complete_config(ctx, 'misc', 'save_bibfile_to')
    save_path_bib = Path(save_dir) / f'{target}.bib'
    make_bibfile_from_records(_fetch_database(ctx), target,
                              config['propnames'], save_path_bib)
    make_abbrjson_from_bibpath(save_path_bib, config['abbr'])

# -- vvv Helper vvv ---

def _fetch_database(ctx: Context) -> NotionDatabase:
    tokenkey = _complete_config(ctx, 'database', 'tokenkey')
    database_id = _complete_config(ctx, 'database', 'database_id')
    return NotionDatabase(tokenkey, database_id)


def _complete_config(ctx: Context, section: str, key: str) -> str:
    """Prompt user to input missing config value and update file."""
    EXPLAIN_MAP = {
        'tokenkey': 'Notion integration token key',
        'database_id': 'Notion database ID',
        'save_bibfile_to': 'Directory to save BIB file',
    }

    config = ctx.obj['config']
    if not (val:=config[section].get(key)):
        val = click.prompt(f'Please enter {EXPLAIN_MAP[key]}')
        config[section][key] = val
        save_config(config)
    return val

if __name__ == '__main__':
    main()  # type: ignore
