"""Postman Collection Importer Service.

Phase 1 scope:
 - Load collection JSON and optional environment JSON
 - Compute hash, upsert ApiCollection
 - Flatten items (recursive) into ApiRequest rows
 - Normalize paths: replace :var and {{var}} with {var}
 - Extract variable usage ({{var}}) in URL, headers, body
 - Mark unresolved variables (those not present in environment snapshot)
 - Classify mutation methods (POST/PUT/PATCH/DELETE)
 - Attempt endpoint linkage (simple match: method + normalized path suffix match)

Deferred (future phases):
 - Advanced test script parsing (events)
 - Variable production tracking via test scripts
 - Smart endpoint inference (templated path variable matching)
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Iterable, Set
import re

from sqlmodel import Session

from database.repositories.unit_of_work import UnitOfWork
from database.repositories.api_collections_repository import ApiCollectionsRepository
from database.repositories.api_requests_repository import ApiRequestsRepository
from database.repositories.application_endpoints_repository import ApplicationEndpointRepository
from database.models.api_collections import ApiRequest


VARIABLE_PATTERN = re.compile(r"{{\s*([A-Za-z0-9_\-\.]+)\s*}}")
PATH_VAR_PATTERN = re.compile(r":([A-Za-z0-9_]+)")


class PostmanImportResult(Dict[str, Any]):
    """Typed-ish result container."""


class PostmanImporter:
    def __init__(
        self,
        session: Session,
        *,
        uow: Optional[UnitOfWork] = None,
    ):
        self.session = session
        self.uow = uow or UnitOfWork(session)  # direct if outside factory
        self.collections_repo: ApiCollectionsRepository = self.uow.api_collections
        self.requests_repo: ApiRequestsRepository = self.uow.api_requests
        self.endpoints_repo: ApplicationEndpointRepository = ApplicationEndpointRepository(session)

    # ---------- Public API ----------
    def import_collection(
        self,
        collection_path: Path,
        *,
        environment_path: Optional[Path] = None,
        mapping_id: Optional[int] = None,
        store_raw: bool = True,
    ) -> PostmanImportResult:
        collection_json = json.loads(collection_path.read_text())
        environment_json = (
            json.loads(environment_path.read_text()) if environment_path and environment_path.exists() else None
        )

        env_snapshot, secret_names = self._extract_environment_snapshot(environment_json)
        raw_serialized = json.dumps(collection_json, separators=(",", ":"))
        raw_hash = hashlib.sha256(raw_serialized.encode("utf-8")).hexdigest()

        api_collection = self.collections_repo.create_collection(
            name=collection_json.get("info", {}).get("name", "Unnamed Collection"),
            raw_hash=raw_hash,
            mapping_id=mapping_id,
            source_raw=raw_serialized if store_raw else None,
            environment_snapshot=env_snapshot or None,
            secret_variables={"masked": secret_names} if secret_names else None,
        )

        # If requests already exist for this collection, short-circuit (idempotent)
        existing_count = self.requests_repo.count(collection_id=api_collection.id)
        if existing_count > 0:
            return PostmanImportResult(
                collection_id=api_collection.id,
                reused=True,
                requests=existing_count,
            )

        flat_items: List[Tuple[List[str], Dict[str, Any]]] = []
        self._flatten_items(collection_json.get("item", []), [], flat_items)

        requests: List[ApiRequest] = []
        for path_stack, item in flat_items:
            request_block = item.get("request")
            if not request_block:
                continue
            method = (request_block.get("method") or "GET").upper()
            url_info = request_block.get("url")
            normalized_path, full_template, path_vars = self._normalize_url(url_info)
            headers_block = request_block.get("header") or []
            headers = self._collect_key_values(headers_block)
            query_params = self._collect_query(url_info)
            body_mode, body_raw, body_json = self._parse_body(request_block.get("body"))
            auth_json = request_block.get("auth") if isinstance(request_block.get("auth"), dict) else None
            events_json = self._extract_events(item.get("event"))

            var_refs: Set[str] = set()
            var_refs.update(self._find_variables(full_template or ""))
            var_refs.update(self._find_variables(json.dumps(headers)))
            if body_raw:
                var_refs.update(self._find_variables(body_raw))
            unresolved = sorted([v for v in var_refs if env_snapshot and v not in env_snapshot]) if var_refs else []

            api_request = ApiRequest(
                collection_id=api_collection.id,  # type: ignore[arg-type]
                original_name=item.get("name"),
                http_method=method,
                normalized_path=normalized_path or "/",
                full_url_template=full_template,
                headers_json=headers or None,
                query_params_json=query_params or None,
                body_mode=body_mode,
                body_raw=body_raw,
                body_json=body_json,
                auth_json=auth_json,
                path_vars_json=path_vars or None,
                consumes_vars_json=sorted(var_refs) or None,
                produces_vars_json=None,
                order_index=len(requests),
                is_mutation=method in {"POST", "PUT", "PATCH", "DELETE"},
                needs_runtime_injection=bool(unresolved),
                unresolved_vars=unresolved or None,
                events_json={"events": events_json} if events_json else None,
            )

            # Attempt endpoint linkage (basic exact method + path match ignoring leading slashes)
            endpoint_id = self._match_endpoint(method, normalized_path)
            if endpoint_id:
                api_request.endpoint_id = endpoint_id
            requests.append(api_request)

        if requests:
            self.requests_repo.bulk_create(requests)

        return PostmanImportResult(
            collection_id=api_collection.id,
            reused=False,
            requests=len(requests),
            unresolved_requests=sum(1 for r in requests if r.unresolved_vars),
            linked_endpoints=sum(1 for r in requests if r.endpoint_id),
        )

    # ---------- Helpers ----------
    def _extract_environment_snapshot(self, env_json: Optional[Dict[str, Any]]):
        if not env_json:
            return None, []
        values = env_json.get("values") or []
        snapshot = {}
        secret_names = []
        for v in values:
            key = v.get("key")
            if not key:
                continue
            if v.get("disabled"):
                continue
            val = v.get("value")
            if isinstance(val, str) and self._looks_secret(key, val):
                secret_names.append(key)
                continue
            snapshot[key] = val
        return snapshot, secret_names

    def _looks_secret(self, key: str, value: str) -> bool:
        lowered = key.lower()
        if any(t in lowered for t in ("secret", "password", "token", "apikey", "api_key")):
            return True
        return False

    def _flatten_items(self, items: Iterable[Dict[str, Any]], path_stack: List[str], out: List[Tuple[List[str], Dict[str, Any]]]):
        for entry in items:
            name = entry.get("name") or "unnamed"
            new_stack = path_stack + [name]
            if "item" in entry and isinstance(entry["item"], list):
                self._flatten_items(entry["item"], new_stack, out)
            else:
                out.append((new_stack, entry))

    def _normalize_url(self, url_block: Any) -> Tuple[Optional[str], Optional[str], List[str]]:
        if not url_block:
            return None, None, []
        # Postman may have "raw" or structured segments
        raw = url_block.get("raw") if isinstance(url_block, dict) else None
        if not raw and isinstance(url_block, dict):
            host = url_block.get("host") or []
            path = url_block.get("path") or []
            raw = "/".join([*(host if isinstance(host, list) else [host]), *(path if isinstance(path, list) else [path])])
        if not raw:
            return None, None, []
        # Extract path component after protocol and domain
        path_part = raw
        if "://" in raw:
            path_part = raw.split("://", 1)[1]
            path_part = "/".join(path_part.split("/")[1:])  # drop host
        if not path_part.startswith("/"):
            path_part = "/" + path_part
        # Replace :var with {var}
        path_vars = PATH_VAR_PATTERN.findall(path_part)
        path_part = PATH_VAR_PATTERN.sub(lambda m: "{" + m.group(1) + "}", path_part)
        # Replace {{var}} with {var}
        def repl_var(match):
            return "{" + match.group(1) + "}"  # normalized template

        normalized_path = VARIABLE_PATTERN.sub(repl_var, path_part)
        return normalized_path, raw, path_vars

    def _collect_key_values(self, headers_block: List[Dict[str, Any]]):
        result = {}
        for h in headers_block:
            if h.get("disabled"):
                continue
            key = h.get("key")
            if not key:
                continue
            result[key] = h.get("value")
        return result

    def _collect_query(self, url_block: Any):
        if not isinstance(url_block, dict):
            return None
        query_items = url_block.get("query") or []
        result = {}
        for q in query_items:
            if q.get("disabled"):
                continue
            k = q.get("key")
            if not k:
                continue
            result[k] = q.get("value")
        return result or None

    def _parse_body(self, body_block: Any):
        if not isinstance(body_block, dict):
            return None, None, None
        mode = body_block.get("mode")
        if mode == "raw":
            raw = body_block.get("raw")
            try:
                parsed = json.loads(raw) if raw and raw.strip().startswith("{") else None
            except Exception:
                parsed = None
            return "raw", raw, parsed
        return mode, None, None

    def _extract_events(self, events_block: Any):
        if not isinstance(events_block, list):
            return None
        simplified = []
        for ev in events_block:
            listen = ev.get("listen")
            script = ev.get("script", {})
            if not isinstance(script, dict):
                continue
            lines = script.get("exec") if isinstance(script.get("exec"), list) else None
            simplified.append({"listen": listen, "lines": lines})
        return simplified or None

    def _find_variables(self, content: str) -> Set[str]:
        return set(VARIABLE_PATTERN.findall(content))

    def _match_endpoint(self, method: str, normalized_path: Optional[str]) -> Optional[int]:
        if not normalized_path:
            return None
        # Simple heuristic: exact method + path match ignoring leading slash
        path_no_slash = normalized_path.lstrip('/')
        candidates = self.endpoints_repo.find_by(http_method=method)
        norm_candidates = {
            e.id: (e.endpoint_url.lstrip('/') if getattr(e, 'endpoint_url', None) else '')
            for e in candidates
        }
        for eid, ep_path in norm_candidates.items():
            if ep_path == path_no_slash:
                return eid
        return None


__all__ = ["PostmanImporter", "PostmanImportResult"]
