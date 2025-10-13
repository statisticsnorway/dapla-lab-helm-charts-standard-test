import json
#import pytest
import sys


def main():
    try:
      helm_chart_path = sys.argv[1]
    except Exception:
        raise ValueError("Expected helm chart path argument")
    test_helm_chart_schema(helm_chart_path)

def get_tag(tag_and_date) -> str:
    return tag_and_date.rsplit("-", 1)[0]

source = {
    "jdemetra": {"default": "jd2.2.5",
                 "options": ["jd2.2.5", "jd3.2.4"]},
    "jupyter": {"default": "r4.4.0-py311",
                "options": ["r4.4.0-py311", "r4.4.0-py312"]},
    "jupyter-playground": {"default": "r4.4.0-py311",
                "options": ["r4.4.0-py311", "r4.4.0-py312"]},
    "jupyter-pyspark": {"default": "py311-spark3.5.3",
                        "options": ["py311-spark3.5.3","py312-spark3.5.3"]},
    "rstudio": {"default": "r4.4.0",
                "options": ["r4.3.3", "r4.4.0"]},
    "vscode-python": {"default": "r4.4.0-py311",
                "options": ["r4.4.0-py311", "r4.4.0-py312"]}
}

def test_helm_chart_schema(chart_path: str):
    helm_chart = chart_path.rsplit("/", 1)[1]
    load_path = f"{chart_path}/values.schema.json"
    with open(load_path, "r") as f:
      schema = json.load(f)
    image_version_schema = schema["properties"]["tjeneste"]["properties"]["version"]
    default_image_version = get_tag(image_version_schema["default"])
    image_version_options = [get_tag(tag) for tag in image_version_schema["listEnum"]]

    if not source[helm_chart]["default"] == default_image_version:
        print(f"""
        Unexpected default image tag in the values.schema.json for the helm chart {helm_chart}.
        In the field '.properties.tjeneste.properties.version.default'.

        Got {default_image_version}
        Expected {source[helm_chart]["default"]}
        """)
        sys.exit(1)

    if not source[helm_chart]["options"] == image_version_options:
        print(f"""
        Unexpected image tag list in the values.schema.json for the helm chart {helm_chart}.
        In the field '.properties.tjeneste.properties.version.listEnum'.

        Got {image_version_options}
        Expected {source[helm_chart]["options"]}
        """)
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
