# Postman Collection Import (Phase 1)

This feature ingests a Postman collection (and optional environment) into the QA Intelligence database to enable:

- Normalized storage of requests (method, path, variables, headers, bodies)
- Future performance / simulation generation
- Mapping to existing application endpoints

## Data Model

Tables introduced:

- `api_collections`: One row per imported collection (hash de-duplicates)
- `api_requests`: Flattened, ordered list of requests

Key JSON fields on `api_requests`:

- `headers_json`, `query_params_json`: Request metadata
- `body_json` + `body_raw`: Raw + parsed body (if simple JSON)
- `auth_json`: Raw Postman auth block
- `path_vars_json`: Path variables detected from `:var` or templated `{{var}}`
- `consumes_vars_json`: Variables referenced in URL/headers/body
- `unresolved_vars`: Subset of variables not defined in environment during import
- `events_json`: Minimal capture of test/prerequest scripts (phase 1 – structure only)

## Normalization Rules

- `:var` → `{var}`
- `{{varName}}` inside paths → `{varName}` (templating normalization)
- Variable detection uses regex `{{ var }}` scanning URL, headers, and raw body
- Mutation detection: method in `POST|PUT|PATCH|DELETE`

## Endpoint Linking (Basic Heuristic)

Exact match on `http_method` + normalized path (ignoring leading slash) against existing `application_endpoints.endpoint_url`.

Future improvements may include pattern matching for templated segments.

## Import Idempotency

Hash (`raw_hash`) computed from minified collection JSON; if collection already exists and has requests, importer reuses existing data.

## CLI Usage

```bash
python scripts/import_postman.py --collection postman_collection.json \
    --environment postman_env.json --mapping-id 5
```

Flags:

- `--no-raw` skips storing full raw collection JSON
- `--mapping-id` associates collection with `app_environment_country_mappings` row

Output: JSON summary with counts, unresolved and linked endpoints.

## Return Summary Fields

- `collection_id`
- `reused` (bool)
- `requests` (total imported)
- `unresolved_requests` (# with unresolved vars)
- `linked_endpoints` (# matched to existing endpoints)

## Safety & Secrets

Environment variables with names containing `secret|password|token|apikey|api_key` are NOT stored (only the key added to `secret_variables.masked`).

## Next Phases (Not Yet Implemented)

- Script parsing to derive produced variables
- Advanced templated path matching & partial similarity mapping
- Conflict detection & drift reporting
- Scenario generation for performance test configuration

## Testing Recommendations

1. Migration idempotency: run migration twice; second run should be a no-op.
2. Import same collection twice: second run returns `reused=True`.
3. Import with environment missing some variables: verify `unresolved_vars` populated.
4. Endpoint linkage: create a matching `application_endpoints` entry and confirm `endpoint_id` set.

---
Phase 1 provides foundational persistence; later phases will build automation on top of this structured layer.

## Agent Tool & WebSocket Attachment Usage (Phase 1.1)

You can now upload a Postman collection (and optional environment) directly via the WebSocket `chat_message` envelope using attachments. The server will detect the collection, persist it, and return an `agent_response` with a `postman_import_summary`.

### Attachment Structure

Each attachment (any file type) is accepted and saved; the agent decides what to do. For Postman auto-detection heuristics still consider JSON, but non-JSON files are still persisted and exposed.

Attachment object example (for JSON):

```json
{
    "filename": "My Collection.postman_collection.json",
    "mime_type": "application/json",
    "content": "<base64-encoded-json>"
}
```

Optional environment file uses the same structure (e.g. `My Env.postman_environment.json`).

### Detection Heuristics

- Collection: filename ends with `.postman_collection.json` OR JSON contains `info` and `item` keys.
- Environment: filename ends with `.postman_environment.json` OR JSON contains `values`, `id`, and `name`.
- Maximum decoded size: 5 MB per attachment (oversized files skipped silently).

### Agent Decision vs Auto Import

By default, the server does NOT auto-import. It only stages the uploaded files and augments the user message so the agent can decide whether to call the `postman_import` tool.

To force immediate import, include in `payload.metadata`:

```json
{ "postman_auto_import": true }
```

If omitted or false, the agent will see appended context lines such as:

```text
[ATTACHMENT] Postman collection available:
collection_path=.../temp/websocket_uploads/<session_id>/sample.postman_collection.json
environment_path=... (if provided)
Agent: You may choose to import using the postman_import tool if appropriate.
```

### Example WebSocket Envelope

```json
{
    "type": "chat_message",
    "version": "2.0",
    "payload": {
        "message_type": "chat_message",
        "content": "Import this Postman collection, please.",
        "metadata": { "mapping_id": 5, "postman_auto_import": true },
        "attachments": [
            {
                "filename": "sample.postman_collection.json",
                "mime_type": "application/json",
                "content": "<base64-collection-json>"
            },
            {
                "filename": "sample.postman_environment.json",
                "mime_type": "application/json",
                "content": "<base64-environment-json>"
            }
        ]
    }
}
```

### Response Envelope (Summary)

```json
{
    "type": "agent_response",
    "payload": {
        "message_type": "agent_response",
        "response_type": "postman_import_summary",
        "tools_used": ["postman_import"],
        "content": "Postman collection imported successfully.\nCollection ID: 12\nReused: False\nRequests: 42\nUnresolved Requests: 3\nLinked Endpoints: 9\nMapping ID: 5"
    }
}
```

### Behavior Notes

- All attachments (any type) are persisted under the session directory; their absolute paths are added to `metadata.attachments_paths` for agent inspection.
- If a collection attachment is detected, the import executes before normal agent chat processing (when `postman_auto_import: true`); the summary is returned immediately.
- Errors during import return an `error_event` with code `postman_import_failed` or `postman_import_error`.
- `mapping_id` (if provided in `payload.metadata.mapping_id`) is passed through to associate the collection.
- Files are written under `temp/websocket_uploads/<session_id>/` for traceability.
- Set `postman_chain: true` (with `postman_auto_import: true`) to continue the normal agent conversation after the import summary.
- Without `postman_auto_import`, the agent decides; the tool paths are exposed in `metadata` (`postman_collection_path`, `postman_environment_path`).
- If no collection is detected you still receive a `postman_attachment_unrecognized` diagnostic event and the conversation continues (attachments are still staged for agent tools or manual reasoning).

### Progress & Completion Events

When `postman_auto_import: true` the server emits system events:

1. `postman_import_start` – includes `collection_path`, optional `environment_path`, `mapping_id`.
2. (Future) `postman_import_processing` – reserved for granular steps (not yet emitted).
3. `postman_import_complete` – includes the import result summary fields plus file paths.

### Diagnostic Event (Attachment Not Recognized)

If attachments are present but no valid Postman collection pattern is detected, the server now emits:

`postman_attachment_unrecognized` (system_event)

Payload fields:

- `attachments_count`: total attachments provided
- `inspected`: number iterated with JSON structure checks
- `reasons`: up to 20 short reason codes explaining skips (e.g. `file.txt:not_json_like`, `big.postman_collection.json:too_large:7340032`, `name.json:no_postman_signature`)

Use this to surface actionable UI feedback when a user expects an import but nothing happens.

Clients can listen for these to update UI progress indicators.

### Temporary Upload Retention

Uploaded session directories under `temp/websocket_uploads/` are cleaned every 30 minutes; any directory older than 6 hours (based on last modification time) is removed. Adjusting retention would require changing `upload_retention_seconds` in `WebSocketServer`.

### Limitations (Current)

- No parallel collection imports per single message.
- Does not chain follow-up agent reasoning after import (future enhancement: continue conversation automatically).
- No cleanup task yet for uploaded temp files (manual or future scheduled cleanup recommended).

---
This WebSocket integration layer (Phase 1.1) enables real-time ingestion without dropping to CLI, completing the initial end-to-end flow from client upload → normalized persistence → immediate structured feedback.
