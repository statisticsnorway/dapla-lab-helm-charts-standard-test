# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo-studio==0.4.0",
# ]
# ///

from docutils.utils.math.latex2mathml import over
import argparse
import asyncio
import curses
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import NoReturn

IS_DAPLA_ENVIRONMENT = "DAPLA_ENVIRONMENT" in os.environ
MARIMO_ADDRESS = f"http://localhost:{8080 if IS_DAPLA_ENVIRONMENT else 2718}"
def green_text(value: Path | str) -> str:
    return f"\033[32m{value}\033[0m"


def parse_args() -> str:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser(
        "html", help="Opprett en html-side for notebooken med SSB-tema"
    )
    subparsers.add_parser(
        "docs", help="Last ned relevant, oppdatert dokumentasjon for agenten"
    )
    return parser.parse_args().command


def main() -> None:
    command = parse_args()
    if command == "docs":
        fetch_docs()
        return

    notebooks = find_active_notebooks()
    notebook_file = (
        exit_because_no_valid_marimo_session()
        if not notebooks
        else notebooks[0]
        if len(notebooks) == 1
        else choose_notebook(notebooks)
    )
    create_view(notebook_file)


def fetch_docs() -> None:
    fetch_github_docs("statisticsnorway/dapla-manual", "dapla-manual/statistikkere")
    fetch_github_docs("digdir/designsystemet", "apps/www/app/content")


def exit_because_no_valid_marimo_session() -> NoReturn:
    print(
        "Du må ha en Marimo-fil som er lagret under dashboards-mappa og er åpnet i Marimo-grensesnittet.",
        file=sys.stderr,
    )
    raise SystemExit(1)


def find_active_notebooks() -> list[Path]:
    try:
        with urllib.request.urlopen(
            f"{MARIMO_ADDRESS}/api/sessions", timeout=2
        ) as response:
            sessions = json.load(response)
    except Exception:
        exit_because_no_valid_marimo_session()

    if not isinstance(sessions, dict):
        exit_because_no_valid_marimo_session()

    return [
        Path(session["path"])
        for session in sessions.values()
        if isinstance(session, dict)
        and isinstance(session.get("path"), str)
        and Path(session["path"]).is_file()
        and Path(session["path"]).parent.name == "dashboards"
    ]


def create_view(notebook_file: Path) -> Path:
    return asyncio.run(_create_view(notebook_file))


async def _create_view(notebook_file: Path) -> None:
    from marimo_studio.authoring import open_workspace

    workspace = open_workspace(notebook_file)
    overview = await workspace.status()

    if (
        overview.default_view is not None
        and (overview.view_root / overview.default_view).is_dir()
    ):
        print(
            f"En html-side for notebooken eksisterer allerede i mappen {green_text(overview.view_root / overview.default_view)}."
        )
        return

    print("Oppretter nytt view...")
    view = await workspace.create_view(
        "dashboard",
        starter="marimo-studio/vanilla:default",
        make_default=True,
    )
    document = await view.read("index.html")
    if "</head>" in document.content:
        content = document.content.replace(
            "</head>", f"{get_ssb_style_block()}\n</head>", 1
        )
        await view.write("index.html", content, expected_revision=document.revision)
    await view.build()
    print(
        "En nytt html-side med SSB-tema er opprettet for notebooken. Last inn siden på nytt for å vise det."
    )
    view_folder = Path((await view.inspect()).root)
    print(f"Html-siden ligger under mappen {green_text(view_folder)}. Denne bør commites til git")


def get_ssb_style_block() -> str:
    return """<!-- Do not remove this style block. -->
<style>
@import url("https://cdn.jsdelivr.net/npm/@digdir/designsystemet-css@1.23.0/dist/src/index.css");
@import url("https://cdn.jsdelivr.net/npm/@statisticsnorway/design-css@0.2.4/dist/src/fonts/fonts.css");
@import url("https://cdn.jsdelivr.net/npm/@statisticsnorway/design-css@0.2.4/dist/theme/ssb.css");

:root {
  --marimo-cell-font: var(--ds-font-family);
  --marimo-cell-heading-font: var(--ds-font-family);
  --marimo-cell-background: var(--ds-color-background-default);
  --marimo-cell-foreground: var(--ds-color-text-default);
  --marimo-cell-surface: var(--ds-color-surface-default);
  --marimo-cell-border-color: var(--ds-color-border-subtle);
  --marimo-cell-accent: var(--ds-color-base-default);
  --marimo-cell-error: var(--ds-color-base-default);
  --marimo-cell-radius: var(--ds-border-radius-default);
  --marimo-cell-padding: var(--ds-size-4);
}
</style>"""


def fetch_github_docs(repo_name: str, docs_path: str) -> Path:
    destination = Path.home() / ".cache" / repo_name
    print(f"Henter relevant dokumentasjon: {green_text(destination)}...")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temporary:
        subprocess.run(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                f"https://github.com/{repo_name}.git",
                temporary,
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["git", "-C", temporary, "sparse-checkout", "set", docs_path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(Path(temporary) / docs_path, destination)
    return destination


def choose_notebook(notebooks: list[Path]) -> Path:
    return notebooks[curses.wrapper(_choose_notebook, notebooks)]


def _choose_notebook(screen: curses.window, notebooks: list[Path]) -> int:
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
    selected = 0
    while True:
        screen.clear()
        screen.addstr("Velg Marimo-fil:\n\n")
        for index, notebook in enumerate(notebooks):
            screen.addstr(
                f"{'❯ ' if index == selected else '  '}{notebook}\n",
                curses.color_pair(1) if index == selected else 0,
            )
        screen.addstr("\nBruk ↑/↓ og trykk Enter.")
        key = screen.getch()
        if key == curses.KEY_UP:
            selected = (selected - 1) % len(notebooks)
        elif key == curses.KEY_DOWN:
            selected = (selected + 1) % len(notebooks)
        elif key in (curses.KEY_ENTER, 10, 13):
            return selected


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
        raise SystemExit(130)
