# oncall-handoff-brief config

Edit `config.json` to enable automated signal sources.

| Field | Type | Description |
|---|---|---|
| `atlas_app_names` | string[] | Atlas application names for metrics/alerts (e.g. `["search-api", "etl-daily"]`) |
| `spinnaker_apps` | string[] | Spinnaker application names for deploy status |
| `maestro_workflow_owners` | string[] | Maestro workflow owners for pipeline health (e.g. `["data.platform.myteam"]`) |
| `slack_channel_ids` | string[] | Slack channel IDs for incident thread search (e.g. `["C01ABC123"]`) |
| `lookback_days` | number | How far back to check (default: 7) |

Populate arrays with your team's values. Empty arrays are skipped during report generation.
