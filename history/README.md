# History Folder

This folder tracks legacy/archival items that are no longer part of the active workflow.

## Current archival policy

- Active runtime docs stay in repository root.
- Legacy migration/cleanup artifacts are moved out of root.
- If a removed file is needed, recover it from git history.

## Archived in this cleanup

- Legacy env-template workflow (`env.example`) replaced by `.env.example` + `config.yaml` templates.
- One-off cleanup/analysis docs removed from root in favor of focused operational docs.
