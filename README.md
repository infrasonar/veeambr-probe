[![CI](https://github.com/infrasonar/veeambr-probe/workflows/CI/badge.svg)](https://github.com/infrasonar/veeambr-probe/actions)
[![Release Version](https://img.shields.io/github/release/infrasonar/veeambr-probe)](https://github.com/infrasonar/veeambr-probe/releases)

# InfraSonar Veeam Backup & Replication Probe

Documentation: https://docs.infrasonar.com/collectors/probes/veeambr/

## Environment variable

Variable            | Default                        | Description
------------------- | ------------------------------ | ------------
`AGENTCORE_HOST`    | `127.0.0.1`                    | Hostname or Ip address of the AgentCore.
`AGENTCORE_PORT`    | `8750`                         | AgentCore port to connect to.
`INFRASONAR_CONF`   | `/data/config/infrasonar.yaml` | File with probe and asset configuration like credentials.
`MAX_PACKAGE_SIZE`  | `500`                          | Maximum package size in kilobytes _(1..2000)_.
`MAX_CHECK_TIMEOUT` | `300`                          | Check time-out is 80% of the interval time with `MAX_CHECK_TIMEOUT` in seconds as absolute maximum.
`DRY_RUN`           | _none_                         | Do not run demonized, just return checks and assets specified in the given yaml _(see the [Dry run section](#dry-run) below)_.
`LOG_LEVEL`         | `warning`                      | Log level (`debug`, `info`, `warning`, `error` or `critical`).
`LOG_COLORIZED`     | `0`                            | Log using colors (`0`=disabled, `1`=enabled).
`LOG_FMT`           | `%y%m%d %H:%M:%S`              | Log format prefix.

## Config

Only Grant Type `password` is currently supported.

```yaml
veeambr:
  config:
    grantType: password
    username: my_user_name
    password: xxxxxxxxxxxx
```

## Docker build

```
docker build -t veeambr-probe . --no-cache
```

## Dry run

Available checks:
- `backups`
- `malwareEvents`

Create a yaml file, for example _(test.yaml)_:

```yaml
asset:
  name: "backup.foo.local"
  check: "backups"
  config:
    verifySSL: false
    port: 4443
    apiVersion: 1.2.-rev1
    backupMaxAge: 7
    malwareMaxAge: 7
```

Run the probe with the `DRY_RUN` environment variable set the the yaml file above.

```
DRY_RUN=test.yaml python main.py
```
