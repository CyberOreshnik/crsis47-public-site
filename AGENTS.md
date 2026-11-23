# Codex research source-use workflow (development only)

For CRSIS-47 research tasks performed in this repository:

1. When a **synthetic** article or source is actually selected and used, prepare one `SOURCE_USED` JSON event using `source-hub-api/synthetic-event.json` as the schema example. Do not invent author, DOI, publisher or publication dates; use null/[] for unknown fields. Preserve source/project/claim IDs.
2. If the local private Source Hub service is running and `SOURCE_HUB_INTAKE_TOKEN` is available, invoke `python source-hub-api/codex_capture.py PATH_TO_EVENT_JSON` immediately after use. This command submits the event and polls until the worker confirms `filed`. Report the returned source ID and receipt.
3. If the service is unavailable, the record is restricted, the URL is not an approved synthetic example.org URL, or filing fails, **do not claim filing**. Report `NOT FILED` and the blocking reason. Do not silently bypass the controls or commit a backlog of unfiled records to this public repository.
4. Never commit credentials, private SQLite files, WAL files, research originals, restricted metadata or protected material. Do not call `project.py --approve-synthetic` as part of automatic filing. Public projection is a separate explicit approval.
5. Do not merge, deploy, enable real-source ingestion, or perform doctoral experimental execution under this instruction.

This is an explicit repository-level Codex workflow convention, **not a universal automatic hook** for ChatGPT, Zotero, browser research, or Codex outside this repository. Actual automatic invocation depends on Codex executing this workflow. See `source-hub-api/INGESTION.md` for local service setup.
