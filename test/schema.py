# /// script
# dependencies = [
#   "termcolor"
# ]
# ///

import json
import re
import sys

from termcolor import cprint


def main():
    try:
      helm_chart_path = sys.argv[1]
    except Exception:
        raise ValueError("Expected helm chart path argument")
    test_helm_chart_schema(helm_chart_path)


DATE_SUFFIX = re.compile(r"-\d{4}\.\d{2}\.\d{2}T\d{2}_\d{2}Z$")


def get_tag(tag_and_date) -> str:
    """Strip the build date suffix (e.g. '-2026.10.26T01_31Z') if present."""
    return DATE_SUFFIX.sub("", tag_and_date)


# Path (under .properties) to the image version field in values.schema.json
TJENESTE_VERSION = ["tjeneste", "version"]
TJENESTE_IMAGE_VERSION = ["tjeneste", "image", "version"]

# Expected image tags (without date suffix) for every chart in charts/.
# "options" is None when the schema has no listEnum.
source = {
    "datadoc": {"path": TJENESTE_IMAGE_VERSION,
                "default": "v1",
                "options": None},
    "jdemetra": {"path": TJENESTE_VERSION,
                 "default": "jd2.2.5",
                 "options": ["jd2.2.5", "jd3.9.0"]},
    "jupyter": {"path": TJENESTE_VERSION,
                "default": "r4.6.0-py313",
                "options": ["r4.6.0-py313", "r4.4.0-py313"]},
    "jupyter-playground": {"path": TJENESTE_VERSION,
                           "default": "r4.6.0-py313",
                           "options": ["r4.6.0-py313", "r4.4.0-py313"]},
    "jupyter-pyspark": {"path": TJENESTE_VERSION,
                        "default": "py313-spark4.1.2",
                        "options": ["py313-spark4.1.2"]},
    "marimo": {"path": TJENESTE_VERSION,
               "default": "latest",
               "options": ["latest"]},
    "marimo-dashboard": {"path": TJENESTE_VERSION,
                         "default": "latest",
                         "options": ["latest"]},
    "parqueditor": {"path": TJENESTE_VERSION,
                    "default": "latest",
                    "options": ["latest"]},
    "rstudio": {"path": TJENESTE_VERSION,
                "default": "r4.6.0",
                "options": ["r4.6.0", "r4.4.0"]},
    "vardef-forvaltning": {"path": TJENESTE_VERSION,
                           "default": "r4.4.0-py313",
                           "options": None},
    "vscode": {"path": TJENESTE_VERSION,
               "default": "r4.6.0-py313",
               "options": ["r4.6.0-py313", "r4.4.0-py313"]},
}


def get_property(schema: dict, path: list[str]) -> dict:
    node = schema
    for key in path:
        node = node["properties"][key]
    return node


def test_helm_chart_schema(chart_path: str):
    helm_chart = chart_path.rstrip("/").rsplit("/", 1)[-1]

    if helm_chart not in source:
        cprint(f"""
        No expected image tags registered for the helm chart {helm_chart}.
        Add an entry for it to 'source' in test/schema.py.
        """, color="red", no_color=False)
        sys.exit(1)
    expected = source[helm_chart]
    field = ".properties." + ".properties.".join(expected["path"])

    load_path = f"{chart_path}/values.schema.json"
    with open(load_path, "r") as f:
      schema = json.load(f)
    image_version_schema = get_property(schema, expected["path"])
    default_image_version = get_tag(image_version_schema["default"])
    list_enum = image_version_schema.get("listEnum")
    image_version_options = None if list_enum is None else [get_tag(tag) for tag in list_enum]

    if not expected["default"] == default_image_version:
        cprint(f"""
        Unexpected default image tag in the values.schema.json for the helm chart {helm_chart}.
        In the field '{field}.default'.

        Expected {expected["default"]}
        Got {default_image_version}
        """, color="red", no_color=False)
        sys.exit(1)

    if not expected["options"] == image_version_options:
        cprint(f"""
        Unexpected image tag list in the values.schema.json for the helm chart {helm_chart}.
        In the field '{field}.listEnum'.

        Expected {expected["options"]}
        Got {image_version_options}
        """, color="red", no_color=False)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()

