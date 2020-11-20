import os
import json
import pathlib
import sys

import click

import api
import scraping.scrape

import batch


@click.group()
def cli():
    pass


@cli.command(name="api")
@click.option("--debug", default=False, help="run the flask instance in debug mode", show_default=True)
@click.option(
    "--file",
    default="sample.db",
    help="provide the path to an existing sqlite database file",
    type=click.Path(),
    show_default=True,
)
@click.option("--host", default="0.0.0.0", help="the address on which to run the api", show_default=True)
@click.option("--port", default=5001, help="the port on which to run the API", show_default=True)
@click.option(
    "--create/--no-create",
    help="create a new database if one doesn't exist",
    type=bool,
    default=True,
    show_default=True,
)
def run(host: str, port: int, file: str, debug: bool, create=bool):
    db_file = pathlib.Path(file).absolute()
    api.app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_file}"

    if not db_file.exists() and create:
        api.db.drop_all()
        api.db.create_all()

    elif not db_file.exists() and not create:
        click.echo("Error: No database file was found or could be created.", err=True)
        sys.exit(1)

    api.app.run(debug=debug, host=host, port=port)


@cli.command(name="import")
@click.option(
    "-i",
    "--in",
    "json_file",
    required=True,
    help="the path to the input file or directory to be imported",
    type=click.Path(),
)
@click.option(
    "-o", "--out", "db_file", help="the name for the output file", type=str, default="questions.db", show_default=True
)
@click.option(
    "--method",
    type=click.Choice(["db", "api"], case_sensitive=False),
    help="the method to use to import the files",
    default="db",
    show_default=True,
)
@click.option("--progress", is_flag=True, help="show a progress bar", default=False, show_default=True)
@click.option("--url", "endpoint", help="the url for the api import endpoint", type=str)
@click.option(
    "--create/--no-create",
    help="create a new database if one doesn't exist",
    type=bool,
    default=True,
    show_default=True,
)
def import_(json_file: str, db_file: str, method: str, progress: bool, endpoint: str, create: bool):
    json_file = pathlib.Path(json_file).absolute()
    db_file = pathlib.Path(os.getcwd(), db_file).absolute()
    api.app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_file}"

    if not db_file.exists() and create:
        api.db.drop_all()
        api.db.create_all()

    elif not db_file.exists() and not create:
        click.echo("Error: No database file was found or could be created.", err=True)
        sys.exit(1)

    if (method == "api") and (endpoint == None):
        click.echo("Error: Missing option '--url' for the url endpoint when using api import.", err=True)
        sys.exit(1)

    batch.add(filename=str(json_file.absolute()), method=method, url=endpoint, shortnames=True, progress=progress)


@cli.group()
def scrape():
    pass

@scrape.command(name="seasons")
@click.option("--out", "season_file", help="file to store season urls", type=str, default="seasons.json", show_default = True)
@click.option("--cache/--no-cache", help="cache files to a local directory", default=False, show_default = True)
@click.option("--cache-path", help="directory to store cached files", type=str)
def seasons(season_file: str, cache: bool, cache_path: str):
    season_file = pathlib.Path(season_file).absolute()

    if False:#season_file.exists():
        with open(season_file, 'r') as input_file:
            data = json.load(input_file)
    
    else:
        data = list()

    if cache:
        if cache_path == None:
            click.echo("Error: A caching path must be supplied when --cache is used", err=True)
            sys.exit(1)

        scraping.scrape.CACHE = True
        scraping.scrape.CACHE_PATH = pathlib.Path(cache_path)

        if not scraping.scrape.CACHE_PATH.exists():
            if click.confirm("The caching directory does not exist. Create it?", abort=True, default=True):
                scraping.scrape.CACHE_PATH.mkdir(parents=True)
            
            else:
                sys.exit()
    
    data = scraping.scrape.get_seasons_game_ids(start=10, stop=11, include_special = True)

    with open(season_file, 'w') as output_file:
        json.dump(data, output_file, indent="\t", sort_keys=True)

if __name__ == "__main__":
    cli()
    # api(host="0.0.0.0", port=5001, file="sample.db", debug=True)
