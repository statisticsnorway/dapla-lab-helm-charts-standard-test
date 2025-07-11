# jupyter-playground

![Version: 0.15.5](https://img.shields.io/badge/Version-0.15.5-informational?style=flat-square) ![Type: application](https://img.shields.io/badge/Type-application-informational?style=flat-square)

Jupyterlab med Python og R og mange vanlige pakker ferdig installert. Passer godt for de som skal lære R og Python uten for mye kompleksitet.

**Homepage:** <https://manual.dapla.ssb.no/statistikkere/jupyter-playground.html>

## Source Code

* <https://github.com/statisticsnorway/dapla-lab-helm-charts-standard-test>
* <https://github.com/statisticsnorway/dapla-lab-helm-charts-library>
* <https://github.com/statisticsnorway/dapla-lab-images>

## Requirements

| Repository | Name | Version |
|------------|------|---------|
| https://statisticsnorway.github.io/dapla-lab-helm-charts-library | library-chart | 4.4.4 |

## Values

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| affinity | object | `{}` |  |
| autoscaling.enabled | bool | `false` |  |
| autoscaling.maxReplicas | int | `100` |  |
| autoscaling.minReplicas | int | `1` |  |
| autoscaling.targetCPUUtilizationPercentage | int | `80` |  |
| avansert.data.mountStandard | bool | `true` |  |
| avansert.startupScript.scriptArgs | string | `""` |  |
| avansert.startupScript.scriptPath | string | `""` |  |
| dapla.group | string | `""` |  |
| dapla.sharedBuckets | list | `[]` |  |
| dapla.sourceData.reason | string | `""` |  |
| dapla.sourceData.requestedDuration | string | `"4h"` |  |
| daplaUser | string | `""` |  |
| deleteJob.clusterRoleName | string | `"onyxia-delete-job"` |  |
| deleteJob.cronHourAtDay | string | `"20"` |  |
| deleteJob.cronMinuteAtDay | string | `"0"` |  |
| deleteJob.enabled | bool | `true` |  |
| deleteJob.imageVersion | string | `"v1.1.0"` |  |
| deleteJob.serviceAccount.annotations | object | `{}` |  |
| deployEnvironment | string | `"DEV"` |  |
| discovery.mlflow | bool | `true` |  |
| diskplass.accessMode | string | `"ReadWriteOnce"` |  |
| diskplass.enabled | bool | `false` |  |
| diskplass.size | string | `"10Gi"` |  |
| environment.group | string | `"users"` |  |
| environment.user | string | `"onyxia"` |  |
| fullnameOverride | string | `""` |  |
| gitConfig.git.cache | string | `""` |  |
| gitConfig.git.configMapName | string | `""` |  |
| gitConfig.git.email | string | `""` |  |
| gitConfig.git.enabled | bool | `false` |  |
| gitConfig.git.name | string | `""` |  |
| gitConfig.github.branch | string | `""` |  |
| gitConfig.github.build | bool | `false` |  |
| gitConfig.github.repository | string | `""` |  |
| gitConfig.github.token | string | `""` |  |
| global.suspend | bool | `false` |  |
| imagePullSecrets | list | `[]` |  |
| init.regionInit | string | `""` |  |
| init.standardInitPath | string | `"/opt/onyxia-init.sh"` |  |
| istio.enabled | bool | `false` |  |
| istio.gateways[0] | string | `"istio-namespace/example-gateway"` |  |
| istio.hostname | string | `"chart-example.local"` |  |
| kubernetes.enabled | bool | `false` |  |
| maskinportenGuardianUrl | string | `""` |  |
| mlflow.configMapName | string | `""` |  |
| nameOverride | string | `""` |  |
| networking.clusterIP | string | `"None"` |  |
| networking.service.port | int | `8888` |  |
| networking.sparkui.port | int | `4040` |  |
| networking.type | string | `"ClusterIP"` |  |
| nodeSelector | object | `{}` |  |
| oidc.configMapName | string | `""` |  |
| oidc.enabled | bool | `true` |  |
| oidc.tokenExchangeUrl | string | `""` |  |
| podAnnotations | object | `{}` |  |
| podDisruptionBudget.enabled | bool | `true` |  |
| podLabels."onyxia.app" | string | `"jupyterlab"` |  |
| podSecurityContext.fsGroup | int | `100` |  |
| replicaCount | int | `1` |  |
| repository.condaRepository | string | `""` |  |
| repository.configMapName | string | `""` |  |
| repository.pipRepository | string | `""` |  |
| resources.cpu | string | `""` |  |
| resources.memory | string | `""` |  |
| security.allowlist.enabled | bool | `false` |  |
| security.allowlist.ip | string | `"0.0.0.0/0"` |  |
| security.networkPolicy.enabled | bool | `false` |  |
| security.networkPolicy.from | list | `[]` |  |
| security.oauth2.authenticatedEmails | string | `""` |  |
| security.oauth2.clientId | string | `"my-client"` |  |
| security.oauth2.oidcIssuerUrl | string | `"overwritten-by-onyxia"` |  |
| security.oauth2.provider | string | `"keycloak-oidc"` |  |
| security.serviceEntry.enabled | bool | `true` |  |
| security.serviceEntry.hosts[0] | string | `"storage.googleapis.com"` |  |
| securityContext | object | `{}` |  |
| serviceAccount.annotations | object | `{}` |  |
| serviceAccount.create | bool | `true` |  |
| serviceAccount.name | string | `""` |  |
| startupProbe.failureThreshold | int | `60` |  |
| startupProbe.initialDelaySeconds | int | `10` |  |
| startupProbe.periodSeconds | int | `10` |  |
| startupProbe.successThreshold | int | `1` |  |
| startupProbe.timeoutSeconds | int | `5` |  |
| statbankBaseUrl | string | `""` |  |
| statbankEncryptUrl | string | `""` |  |
| statbankTestBaseUrl | string | `""` |  |
| statbankTestEncryptUrl | string | `""` |  |
| tjeneste.image.pullPolicy | string | `"IfNotPresent"` |  |
| tjeneste.version | string | `"r4.4.0-py311-2025.07.01T10_37Z"` |  |
| tolerations | list | `[]` |  |
| userAttributes.environmentVariableName | string | `"OIDC_TOKEN"` |  |
| userAttributes.userAttribute | string | `"access_token"` |  |
| userAttributes.value | string | `""` |  |

----------------------------------------------
Autogenerated from chart metadata using [helm-docs v1.11.0](https://github.com/norwoodj/helm-docs/releases/v1.11.0)
