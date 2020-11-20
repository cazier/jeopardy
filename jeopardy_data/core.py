import os
import pathlib
import sys

import click

import api

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
    db_file = pathlib.Path(file).absolute()
    api.app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_file}"

    api.app.run(debug=debug, host=host, port = port)

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
def import_(json_file: str, db_file: str, method: str, progress: bool, endpoint: str, create: bool):
    json_file = pathlib.Path(json_file).absolute()
    db_file = pathlib.Path(os.getcwd(), db_file).absolute()
    api.app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_file}"


    if not db_file.exists():            
        api.db.drop_all()
        api.db.create_all()

    if (method == "api") and (endpoint == None):
        click.echo("Error: Missing option '--url' for the url endpoint when using api import.", err=True)
        sys.exit(1)

    batch.add(filename=str(json_file.absolute()), method=method, url=endpoint, shortnames=True, progress=progress)


if __name__ == "__main__":
    cli()
    # api(host="0.0.0.0", port=5001, file="sample.db", debug=True)
