import os
import json
import pathlib
import sys

import click

import api
import tools


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
    "--in", "json_path", required=True, help="path to the imported json file", type=click.Path(exists=True),
)
@click.option("--out", "db_path", help="output file", type=str, default="questions.db", show_default=True)
@click.option(
    "--method",
    type=click.Choice(["db", "api"], case_sensitive=False),
    help="the method to use to import the files",
    default="db",
    show_default=True,
)
@click.option("--shortnames", help="json file uses short length keys", type=bool, default=False, show_default=True)
@click.option("--progress/--no-progress", help="show execution progress", type=bool, default=False, show_default=True)
@click.option("--url", "endpoint", help="the url for the api import endpoint", type=str)
@click.option(
    "--create/--no-create",
    help="create a new database if one doesn't exist",
    type=bool,
    default=True,
    show_default=True,
)
def import_(json_path: str, db_path: str, shortnames: bool, method: str, progress: bool, endpoint: str, create: bool):
    json_file = pathlib.Path(json_path).absolute()
    db_file = pathlib.Path(db_path).absolute()

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

    with open(json_file, "r") as file:
        clues = json.load(file)

    results, errors = tools.batch.add_database(items=clues, progress=progress, shortnames=shortnames)

    click.echo(f"Added {results} clues to sqlite database at {db_file}")

    if len(errors) != 0:
        if click.confirm(
            f"Errors occurred adding {len(errors)} to the database. Store the clues that had errors?", default=True
        ):
            with open(pathlib.Path(json_file.parent, "errors.json").absolute(), "w") as file:
                json.dump(errors, file, indent="\t")

            click.echo(f"File saved to {pathlib.Path(json_file.parent, 'errors.json').absolute()}")


@cli.group()
def scrape():
    pass


@scrape.command(name="list")
@click.argument("item")
@click.option("--season", type=str, help="the season for which to display games")
def list_(item: str, season: str):
    """
    List the identifiers that can be scraped using the j-archive.com dataset.

    Can list by either <game> or <season>, but if season is used, the option <--season> must be supplied
    """
    if item == "seasons":
        click.echo(", ".join(tools.batch.get_list_of_seasons()))

    elif item == "games":
        if season == None:
            click.echo("Error: Missing option '--season' when displaying games.", err=True)
            sys.exit(1)

        else:
            click.echo(", ".join(tools.batch.get_list_of_games(season=season)))


@scrape.command(name="fetch")
@click.argument("item")
@click.option("--identifier", type=str, required=True, help="the identifier (from the url) for the kind to scrape")
@click.option("--cache/--no-cache", help="cache files to a local directory", default=True, show_default=True)
@click.option("--cache-path", help="directory to store cached files", type=str, default=".", show_default=True)
@click.option(
    "--output",
    "output_path",
    help="filename to store output",
    type=str,
    default="jeopardy.json",
    show_default=True,
    required=True,
)
@click.option("--progress/--no-progress", help="show execution progress", type=bool, default=False, show_default=True)
def fetch(item: str, identifier: str, cache: bool, cache_path: str, output_path: str, progress: bool):
    """
    Scrape Jeopardy clue data from the j-archive.com and save as a JSON file.

    This argument must be either <season> or <game>, and requires at least one <identifier>, which can be found from
    the end of the j-archive.com URL, or by using some of the other commands in this tool (see `list` for some examples)

    Multiple scraping passes can be performed by passing a comma-separated list of identifiers.
    
    """
    output_file = pathlib.Path(".", output_path).absolute()

    if output_file.exists():
        click.confirm("A file already exists with this name. Overwrite?", abort=True)

    if cache:
        cache_file = pathlib.Path(cache_path, "fetch_cache").absolute()
        cache_file.parent.mkdir(parents=True, exist_ok=True)

        tools.scrape.CACHE = True
        tools.scrape.CACHE_PATH = str(cache_file)

    if item == "season":
        clues, errors = tools.batch.scrape_season(season_id=identifier, progress=progress)

    elif item == "game":
        clues, errors = tools.batch.scrape_multiple_games(game_ids=identifier.split(","), progress=progress)

    else:
        click.echo("Must fetch either a game or season. Ensure argument is one of those two options.")

    with open(output_file, "w") as file:
        json.dump(clues, file, indent="\t")

    click.echo(f"Successfully parsed out {len(clues)} clue(s), with {len(errors)} error(s)")
    if len(errors) != 0:
        click.echo(f'The following game ids had errors: {", ".join(errors)}')


if __name__ == "__main__":
    cli()
