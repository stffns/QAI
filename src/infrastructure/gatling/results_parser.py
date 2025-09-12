from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from bs4 import BeautifulSoup

    BS_AVAILABLE = True
except ImportError:
    BS_AVAILABLE = False


def _parse_from_html_report_bs(html_path: Path) -> List[Dict[str, Any]]:
    """Parse endpoint statistics from Gatling HTML report using Beautiful Soup (more robust)."""
    if not BS_AVAILABLE:
        # Fallback to regex method
        return _parse_from_html_report(html_path)

    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")
        endpoints = []

        # Find endpoint rows (data-parent="ROOT")
        endpoint_rows = soup.find_all("tr", {"data-parent": "ROOT"})

        for row in endpoint_rows:
            # Extract endpoint name
            name_span = row.find("span", class_="ellipsed-name")
            if not name_span:
                continue

            endpoint_name = name_span.get_text().strip()

            # Skip "All Requests" or empty names
            if endpoint_name in ["All Requests", ""] or not endpoint_name:
                continue

            # Extract metrics from table columns
            value_cells = row.find_all("td", class_=re.compile(r"value.*col-\d+"))

            cols = {}
            for cell in value_cells:
                # Extract column number from CSS class
                classes = cell.get("class", [])
                for cls in classes:
                    if "col-" in cls:
                        col_num = int(cls.split("col-")[1])
                        cols[col_num] = cell.get_text().strip()
                        break

            def safe_int(value, default=0):
                try:
                    return int(value) if value and value != "-" else default
                except (ValueError, TypeError):
                    return default

            def safe_float(value, default=0.0):
                try:
                    return float(value) if value and value != "-" else default
                except (ValueError, TypeError):
                    return default

            total_requests = safe_int(cols.get(2, "0"))
            successful_requests = safe_int(cols.get(3, "0"))
            failed_requests = safe_int(cols.get(4, "0"))

            # Response times and metrics
            rps = safe_float(cols.get(6, "0"))
            min_rt = safe_float(cols.get(7, "0"))
            p50_rt = safe_float(cols.get(8, "0"))
            p75_rt = safe_float(cols.get(9, "0"))
            p95_rt = safe_float(cols.get(10, "0"))
            p99_rt = safe_float(cols.get(11, "0"))
            max_rt = safe_float(cols.get(12, "0"))
            mean_rt = safe_float(cols.get(13, "0"))

            endpoint_data = {
                "name": endpoint_name,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "min_response_time": min_rt,
                "p50_response_time": p50_rt,
                "p75_response_time": p75_rt,
                "p95_response_time": p95_rt,
                "p99_response_time": p99_rt,
                "max_response_time": max_rt,
                "avg_response_time": mean_rt,
                "requests_per_second": rps,
            }

            endpoints.append(endpoint_data)

        return endpoints

    except Exception as e:
        print(f"Error parsing HTML report with Beautiful Soup: {e}")
        # Fallback to regex method
        return _parse_from_html_report(html_path)


def _extract_global_stats_from_html(html_path: Path) -> Dict[str, Any]:
    """Extract global statistics from Gatling HTML report."""
    if not BS_AVAILABLE:
        return {}

    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        soup = BeautifulSoup(content, "html.parser")

        # Find the "All Requests" row (global stats)
        for row in soup.find_all("tr"):
            name_span = row.find("span", class_="ellipsed-name")
            if name_span and name_span.get_text().strip() == "All Requests":
                # Extract values from columns
                value_cells = row.find_all("td", class_=re.compile(r"value.*col-\d+"))
                cols = {}
                for cell in value_cells:
                    classes = cell.get("class", [])
                    for cls in classes:
                        if "col-" in cls:
                            col_num = int(cls.split("col-")[1])
                            cols[col_num] = cell.get_text().strip()
                            break

                def safe_int(value, default=0):
                    try:
                        return int(value) if value and value != "-" else default
                    except (ValueError, TypeError):
                        return default

                def safe_float(value, default=0.0):
                    try:
                        return float(value) if value and value != "-" else default
                    except (ValueError, TypeError):
                        return default

                return {
                    "total": safe_int(cols.get(2, "0")),
                    "ok": safe_int(cols.get(3, "0")),
                    "ko": safe_int(cols.get(4, "0")),
                    "error_rate": safe_float(cols.get(5, "0")),
                    "mean_rps": safe_float(cols.get(6, "0")),
                    "min_rt": safe_float(cols.get(7, "0")),
                    "p50": safe_float(cols.get(8, "0")),
                    "p75": safe_float(cols.get(9, "0")),
                    "p95": safe_float(cols.get(10, "0")),
                    "p99": safe_float(cols.get(11, "0")),
                    "max_rt": safe_float(cols.get(12, "0")),
                    "mean_rt": safe_float(cols.get(13, "0")),
                    "std_dev": safe_float(cols.get(14, "0")),
                }

        return {}

    except Exception as e:
        print(f"Error extracting global stats from HTML: {e}")
        return {}


def _parse_from_html_report(html_path: Path) -> List[Dict[str, Any]]:
    """Parse endpoint statistics from Gatling HTML report."""
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()

        endpoints = []

        # Updated regex to match the Gatling HTML table structure
        # Look for table rows with endpoint data, excluding "All Requests" row
        row_pattern = r'<tr[^>]*data-parent="ROOT"[^>]*>.*?</tr>'
        rows = re.findall(row_pattern, content, re.DOTALL)

        for row in rows:
            # Extract endpoint name from ellipsed-name span
            name_match = re.search(
                r'<span[^>]*class="ellipsed-name"[^>]*>([^<]+)</span>', row
            )
            if not name_match:
                continue

            endpoint_name = name_match.group(1).strip()

            # Skip "All Requests" or empty names
            if endpoint_name in ["All Requests", ""] or not endpoint_name:
                continue

            # Extract metrics from table columns
            # Column structure: col-2=total, col-3=ok, col-4=ko, col-5=error%, col-6=rps,
            # col-7=min, col-8=50th, col-9=75th, col-10=95th, col-11=99th, col-12=max, col-13=mean
            col_values = re.findall(
                r'<td[^>]*class="value[^"]*col-(\d+)"[^>]*>([^<]+)</td>', row
            )

            # Convert to dict for easier access
            cols = {int(num): val.strip() for num, val in col_values}

            def safe_int(value, default=0):
                try:
                    return int(value) if value and value != "-" else default
                except (ValueError, TypeError):
                    return default

            def safe_float(value, default=0.0):
                try:
                    return float(value) if value and value != "-" else default
                except (ValueError, TypeError):
                    return default

            total_requests = safe_int(cols.get(2, "0"))
            successful_requests = safe_int(cols.get(3, "0"))
            failed_requests = safe_int(cols.get(4, "0"))

            # Calculate RPS from total/duration (col-6 might be RPS or we need to calculate)
            rps = safe_float(cols.get(6, "0"))

            # Response times in milliseconds
            min_rt = safe_float(cols.get(7, "0"))
            p50_rt = safe_float(cols.get(8, "0"))
            p75_rt = safe_float(cols.get(9, "0"))
            p95_rt = safe_float(cols.get(10, "0"))
            p99_rt = safe_float(cols.get(11, "0"))
            max_rt = safe_float(cols.get(12, "0"))
            mean_rt = safe_float(cols.get(13, "0"))

            endpoint_data = {
                "name": endpoint_name,
                "total_requests": total_requests,
                "successful_requests": successful_requests,
                "failed_requests": failed_requests,
                "min_response_time": min_rt,
                "p50_response_time": p50_rt,
                "p75_response_time": p75_rt,
                "p95_response_time": p95_rt,
                "p99_response_time": p99_rt,
                "max_response_time": max_rt,
                "avg_response_time": mean_rt,
                "requests_per_second": rps,
            }

            endpoints.append(endpoint_data)

        return endpoints

    except Exception as e:
        print(f"Error parsing HTML report: {e}")
        return []


def _find_stats_json(root: Path) -> Optional[Path]:
    if not root.exists():
        return None
    if root.is_file() and root.name == "stats.json":
        return root
    for dirpath, _, filenames in os.walk(root):
        if "stats.json" in filenames:
            return Path(dirpath) / "stats.json"
    return None


def _find_stats_js(root: Path) -> Optional[Path]:
    """Gatling HTML reports often ship stats in js/stats.js (no stats.json)."""
    if not root.exists():
        return None
    # Common location: <report_dir>/js/stats.js
    candidate = root / "js" / "stats.js"
    if candidate.exists():
        return candidate
    # Fallback: search recursively
    for dirpath, _, filenames in os.walk(root):
        if "stats.js" in filenames:
            return Path(dirpath) / "stats.js"
    return None


def _parse_from_runner_log(results_root: Path) -> Dict[str, Any]:
    """Parse human-readable summary from runner.log as a fallback."""
    log_path = (
        results_root if results_root.is_dir() else results_root.parent
    ) / "runner.log"
    if not log_path.exists():
        return {
            "parsed": False,
            "reason": "runner.log not found",
            "path": str(results_root),
        }
    try:
        text = log_path.read_text(encoding="utf-8", errors="ignore")
        # Extract metrics from the "Global Information" block
        req_m = re.search(
            r"request count\s*\|\s*([0-9,]+)\s*\|\s*([0-9,]+)\s*\|\s*([0-9,\-]+)", text
        )

        def parse_num(s: str) -> Optional[float]:
            try:
                s = s.strip()
                if s == "-":
                    return None
                return float(s.replace(",", ""))
            except Exception:
                return None

        def find_val(label: str) -> Optional[float]:
            m = re.search(label + r"\s*\|\s*([0-9,\.\-]+)", text)
            return parse_num(m.group(1)) if m else None

        total = ok = ko = None
        if req_m:
            total = parse_num(req_m.group(1))
            ok = parse_num(req_m.group(2))
            ko = parse_num(req_m.group(3))

        summary = {
            "parsed": True,
            "path": str(log_path),
            "total": total,
            "ok": ok,
            "ko": ko,
            "p50": find_val(r"percentile \(ms\)\s*\|"),  # placeholder; may not exist
            "p95": find_val(r"95th percentile \(ms\)"),
            "p99": find_val(r"99th percentile \(ms\)"),
            "min_rt": find_val(r"min response time \(ms\)"),
            "max_rt": find_val(r"max response time \(ms\)"),
            "mean_rt": find_val(r"mean response time \(ms\)"),
            "mean_rps": find_val(r"mean throughput \(rps\)"),
        }
        found_any = any(
            v is not None for k, v in summary.items() if k not in ("parsed", "path")
        )
        if not found_any:
            return {
                "parsed": False,
                "reason": "runner.log unparseable",
                "path": str(results_root),
            }
        return summary
    except Exception as e:
        return {
            "parsed": False,
            "reason": f"runner.log parse error: {e}",
            "path": str(results_root),
        }


def parse_gatling_results(results_root: Path) -> Dict[str, Any]:
    """Parse Gatling stats.json under results_root and return a compact summary.

    Returns keys: total, ok, ko, mean_rps, p50, p75, p95, p99, mean_rt, max_rt, min_rt

    Priority order:
    1. HTML report (most reliable)
    2. stats.json
    3. stats.js fallback
    4. runner.log (last resort)
    """

    # PRIORITY 1: Try HTML report first (most reliable)
    html_path = results_root / "index.html"
    if html_path.exists() and BS_AVAILABLE:
        try:
            global_stats = _extract_global_stats_from_html(html_path)
            if global_stats and global_stats.get("total"):
                return {
                    "parsed": True,
                    "source": "html_beautiful_soup",
                    "path": str(html_path),
                    "total": global_stats.get("total"),
                    "ok": global_stats.get("ok"),
                    "ko": global_stats.get("ko"),
                    "mean_rps": global_stats.get("mean_rps"),
                    "p50": global_stats.get("p50"),
                    "p75": global_stats.get("p75"),
                    "p95": global_stats.get("p95"),
                    "p99": global_stats.get("p99"),
                    "mean_rt": global_stats.get("mean_rt"),
                    "min_rt": global_stats.get("min_rt"),
                    "max_rt": global_stats.get("max_rt"),
                    # Extended data for compatibility
                    "global_stats": global_stats,
                }
        except Exception as e:
            print(f"HTML parsing failed, falling back: {e}")

    # PRIORITY 2 & 3: Original stats.json/js logic
    stats_path = _find_stats_json(results_root)
    content_type = "json"
    if not stats_path or not stats_path.exists():
        # Try stats.js fallback
        stats_path = _find_stats_js(results_root)
        content_type = "js" if stats_path else "none"
    if not stats_path or not stats_path.exists():
        # PRIORITY 4: Fallback to runner.log summary when stats files are missing
        return _parse_from_runner_log(results_root)

    try:
        text = stats_path.read_text(encoding="utf-8", errors="ignore")
        if content_type == "js":
            # stats.js usually looks like: var stats = { ... };
            # Extract the first JSON object in the file
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                # Fallback: runner.log
                return _parse_from_runner_log(results_root)
            payload = text[start : end + 1]
            try:
                raw = json.loads(payload)
            except Exception:
                # Fallback: runner.log when JSON extraction fails
                return _parse_from_runner_log(results_root)
            s = raw.get("stats", raw)
        else:
            try:
                raw = json.loads(text)
            except Exception:
                # Fallback: runner.log when JSON parsing fails
                return _parse_from_runner_log(results_root)
            s = raw.get("stats", {})

        def num(d: Dict[str, Any], key: str, sub: str = "total") -> Optional[float]:
            v = d.get(key)
            if isinstance(v, dict):
                v = v.get(sub)
            try:
                return float(v) if v is not None else None
            except Exception:
                return None

        out = {
            "parsed": True,
            "path": str(stats_path),
            "total": num(s, "numberOfRequests"),
            "ok": num(s, "numberOfRequests", "ok"),
            "ko": num(s, "numberOfRequests", "ko"),
            "mean_rps": num(s, "meanNumberOfRequestsPerSecond"),
            "p50": num(s, "percentiles1"),
            "p75": num(s, "percentiles2"),
            "p95": num(s, "percentiles3"),
            "p99": num(s, "percentiles4"),
            "mean_rt": num(s, "meanResponseTime"),
            "min_rt": num(s, "minResponseTime"),
            "max_rt": num(s, "maxResponseTime"),
        }
        return out
    except Exception as e:
        # Last resort fallback to runner.log
        fb = _parse_from_runner_log(results_root)
        if fb.get("parsed"):
            return fb
        return {"parsed": False, "reason": f"parse_error: {e}", "path": str(stats_path)}


def parse_gatling_endpoint_results(results_root: Path) -> list[Dict[str, Any]]:
    """Parse per-endpoint/request metrics from Gatling stats when available.

    Returns a list of { name, total, ok, ko, p50, p75, p95, p99, mean_rt, min_rt, max_rt, mean_rps }.
    When detailed request stats aren't available, falls back to a single item derived from global metrics.

    Priority order:
    1. HTML report with Beautiful Soup (most reliable)
    2. HTML report with regex fallback
    3. stats.json/js parsing
    4. Global stats fallback
    """
    items: list[Dict[str, Any]] = []

    # PRIORITY 1: Try Beautiful Soup HTML parsing first
    html_path = results_root / "index.html"
    if html_path.exists():
        try:
            html_items = _parse_from_html_report_bs(html_path)
            if html_items:
                return html_items
        except Exception as e:
            print(f"Beautiful Soup HTML parsing failed: {e}")

    # PRIORITY 2: Try regex HTML parsing as fallback
    try:
        html_items = _parse_from_html_report(results_root)
        if html_items:
            return html_items
    except Exception:
        pass

    # PRIORITY 3: Try to parse stats.json/js like in parse_gatling_results
    stats_path = _find_stats_json(results_root)
    content_type = "json"
    if not stats_path or not stats_path.exists():
        stats_path = _find_stats_js(results_root)
        content_type = "js" if stats_path else "none"
    if not stats_path or not stats_path.exists():
        # Fallback to global-only from runner.log
        g = parse_gatling_results(results_root)
        if g.get("parsed"):
            items.append(
                {
                    "name": "GLOBAL",
                    "total": g.get("total"),
                    "ok": g.get("ok"),
                    "ko": g.get("ko"),
                    "p50": g.get("p50"),
                    "p75": g.get("p75"),
                    "p95": g.get("p95"),
                    "p99": g.get("p99"),
                    "mean_rt": g.get("mean_rt"),
                    "min_rt": g.get("min_rt"),
                    "max_rt": g.get("max_rt"),
                    "mean_rps": g.get("mean_rps"),
                }
            )
        return items

    try:
        text = stats_path.read_text(encoding="utf-8", errors="ignore")
        if content_type == "js":
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError("invalid stats.js format")
            payload = text[start : end + 1]
            raw = json.loads(payload)
        else:
            raw = json.loads(text)

        contents = raw.get("contents", {})

        def num(d: Dict[str, Any], key: str, sub: str = "total") -> Optional[float]:
            v = d.get(key)
            if isinstance(v, dict):
                v = v.get(sub)
            try:
                return float(v) if v is not None else None
            except Exception:
                return None

        if isinstance(contents, dict) and contents:
            for _, v in contents.items():
                s = v.get("stats", {})
                name = s.get("name") or v.get("name") or "request"
                items.append(
                    {
                        "name": name,
                        "total": num(s, "numberOfRequests"),
                        "ok": num(s, "numberOfRequests", "ok"),
                        "ko": num(s, "numberOfRequests", "ko"),
                        "p50": num(s, "percentiles1"),
                        "p75": num(s, "percentiles2"),
                        "p95": num(s, "percentiles3"),
                        "p99": num(s, "percentiles4"),
                        "mean_rt": num(s, "meanResponseTime"),
                        "min_rt": num(s, "minResponseTime"),
                        "max_rt": num(s, "maxResponseTime"),
                        "mean_rps": num(s, "meanNumberOfRequestsPerSecond"),
                    }
                )
            return items
        # No contents; fallback to global-only
        g = parse_gatling_results(results_root)
        if g.get("parsed"):
            items.append(
                {
                    "name": "GLOBAL",
                    "total": g.get("total"),
                    "ok": g.get("ok"),
                    "ko": g.get("ko"),
                    "p50": g.get("p50"),
                    "p75": g.get("p75"),
                    "p95": g.get("p95"),
                    "p99": g.get("p99"),
                    "mean_rt": g.get("mean_rt"),
                    "min_rt": g.get("min_rt"),
                    "max_rt": g.get("max_rt"),
                    "mean_rps": g.get("mean_rps"),
                }
            )
        return items
    except Exception:
        # On failure, return global-only if possible
        g = parse_gatling_results(results_root)
        if g.get("parsed"):
            return [
                {
                    "name": "GLOBAL",
                    "total": g.get("total"),
                    "ok": g.get("ok"),
                    "ko": g.get("ko"),
                    "p50": g.get("p50"),
                    "p75": g.get("p75"),
                    "p95": g.get("p95"),
                    "p99": g.get("p99"),
                    "mean_rt": g.get("mean_rt"),
                    "min_rt": g.get("min_rt"),
                    "max_rt": g.get("max_rt"),
                    "mean_rps": g.get("mean_rps"),
                }
            ]
        return []


def create_enhanced_summary(results_root: Path) -> Dict[str, Any]:
    """Create an enhanced summary.json with both global and endpoint data.

    This function provides a more complete summary than the standard parse_gatling_results,
    including endpoint-level details and metadata.
    """
    # Get global stats
    global_summary = parse_gatling_results(results_root)

    # Get endpoint stats
    endpoint_data = parse_gatling_endpoint_results(results_root)

    # Find HTML path for metadata
    html_path = results_root / "index.html"
    if not html_path.exists():
        # Try to find HTML report in parent directories
        for parent in [results_root.parent, results_root.parent.parent]:
            potential_html = parent / "index.html"
            if potential_html.exists():
                html_path = potential_html
                break

    # Create enhanced summary
    enhanced = {
        # Maintain compatibility with existing format
        "parsed": global_summary.get("parsed", False),
        "source": global_summary.get("source", "unknown"),
        "path": global_summary.get("path", str(results_root)),
        "total": global_summary.get("total"),
        "ok": global_summary.get("ok"),
        "ko": global_summary.get("ko"),
        "p50": global_summary.get("p50"),
        "p75": global_summary.get("p75"),
        "p95": global_summary.get("p95"),
        "p99": global_summary.get("p99"),
        "min_rt": global_summary.get("min_rt"),
        "max_rt": global_summary.get("max_rt"),
        "mean_rt": global_summary.get("mean_rt"),
        "mean_rps": global_summary.get("mean_rps"),
        # Enhanced data
        "global_stats": global_summary.get("global_stats", {}),
        "endpoints": endpoint_data,
        "endpoint_count": len(endpoint_data),
        # Metadata
        "metadata": {
            "total_endpoints": len(endpoint_data),
            "html_available": html_path.exists(),
            "html_path": str(html_path) if html_path.exists() else None,
            "beautiful_soup_available": BS_AVAILABLE,
        },
    }

    # Add derived metadata if we have complete data
    if enhanced.get("total") is not None and enhanced.get("ok") is not None:
        total = enhanced["total"]
        ok = enhanced["ok"]
        ko = enhanced.get("ko", 0)

        enhanced["metadata"].update(
            {
                "all_passed": ko == 0 and total > 0,
                "all_failed": ok == 0 and total > 0,
                "success_rate": (ok / total * 100.0) if total > 0 else 0.0,
                "failure_rate": (ko / total * 100.0) if total > 0 else 0.0,
            }
        )

    return enhanced
