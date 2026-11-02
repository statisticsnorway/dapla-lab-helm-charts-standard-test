#!/usr/bin/env python3
# /// script
# dependencies = [
#   "pyyaml"
# ]
# ///
"""Injection regression test: render each chart with YAML-breaking payloads.
usage: uv run test/injection_test.py charts
Fails if a payload produces any extra Kubernetes object, or if helm output is not valid YAML.
"""
import subprocess
import sys
from pathlib import Path

import yaml

PAYLOAD = 'x"\n---\napiVersion: rbac.authorization.k8s.io/v1\nkind: ClusterRoleBinding\nmetadata:\n  name: pwned\n#'
# A second payload aimed at breaking out of block scalars / single-quoted contexts
PAYLOAD2 = "x'\n\u2028kind: ClusterRoleBinding\n  evil: true"

STRING_KEYS = [
    "environment.user", "environment.group", "deployEnvironment", "daplaUser",
    "tjeneste.version", "tjeneste.image.version", "tjeneste.image.pullPolicy", "tjeneste.pullPolicy",
    "tjeneste.repository", "tjeneste.githubRepo", "tjeneste.marimoAppFile", "tjeneste.startupCommand",
    "tjeneste.marimoVersion",
    "init.standardInitPath", "init.regionInit", "init.regionInitCheckSum", "init.personalInit", "init.personalInitArgs",
    "avansert.startupScript.scriptPath", "avansert.startupScript.scriptArgs",
    "istio.hostname", "istio.extraHostname", "istio.serviceSubDomain",
    "statbankBaseUrl", "statbankEncryptUrl", "statbankTestBaseUrl", "statbankTestEncryptUrl",
    "suvDaplaApiUrl", "pseudoServiceUrl", "whodatServiceUrl", "maskinportenGuardianUrl",
    "environment.DAPLA_MANUAL_NAMING_STANDARD_URL", "environment.DATADOC_STATISTICAL_SUBJECT_SOURCE_URL",
    "diskplass.existingClaim", "security.oauth2.authenticatedEmails",
    "dapla.group", "dapla.sourceData.reason",
]
NUMERIC_KEYS = ["replicaCount", "networking.service.port", "networking.user.port", "avansert.parquedit.port"]
BASE = ["--set", "resources.cpu=1000m", "--set", "resources.memory=4Gi",
        "--set", "ressurser.requests.cpu=1000m", "--set", "ressurser.requests.memory=4Gi"]


def ensure_dependencies(chart):
    """Fetch library-chart into <chart>/charts if missing (build, falling back to update)."""
    if list((chart / "charts").glob("*.tgz")):
        return
    for cmd in ("build", "update"):
        if subprocess.run(["helm", "dependency", cmd, str(chart)], capture_output=True).returncode == 0:
            return


def render(chart, extra):
    r = subprocess.run(["helm", "template", "t", str(chart), *BASE, *extra], capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def kinds(out):
    return sorted((d.get("kind"), d.get("metadata", {}).get("name")) for d in yaml.safe_load_all(out) if d)


def main():
    root = Path(sys.argv[1])
    failed = False
    for chart in sorted(p for p in root.iterdir() if (p / "Chart.yaml").exists()):
        ensure_dependencies(chart)
        rc, out, err = render(chart, [])
        if rc != 0:
            print(f"{chart.name}: baseline render failed: {err.strip()[:200]}")
            failed = True
            continue
        baseline = kinds(out)
        tested = rejected = 0
        for key in STRING_KEYS + NUMERIC_KEYS:
            for payload in (PAYLOAD, PAYLOAD2):
                rc, out, err = render(chart, ["--set-string", f"{key}={payload}"])
                if rc != 0:
                    # schema validation / template errors rejecting the payload is a pass
                    rejected += 1
                    continue
                tested += 1
                try:
                    got = kinds(out)
                except yaml.YAMLError as e:
                    print(f"{chart.name}: FAIL [{key}] output is not valid YAML: {str(e).splitlines()[0]}")
                    failed = True
                    continue
                extra_objs = sorted(set(got) - set(baseline))
                if extra_objs:
                    print(f"{chart.name}: FAIL [{key}] injected objects: {extra_objs}")
                    failed = True
        print(f"{chart.name}: {tested} payload renders checked, {rejected} rejected by helm")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()

