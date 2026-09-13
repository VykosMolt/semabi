#!/usr/bin/env python3
"""Independent visible evaluator for disclosed dispatch/workshop development fixtures.

Fixture-specific labels and expected values belong to this evaluator, never to
the learner. No application source, client stores, native API, or database is read.
Capture/check visits the collection after recording the immediate and reloaded
detail; those evaluator navigations are intrusive and clear a fixture assignment.
Capture/check run only while onboarding and invocation are idle. Watch mode only
reloads the visible page to sample a transient response during one invocation;
it never clicks a control or claims that the sampled response persists.
Output files are never replaced.
"""
from __future__ import annotations

import argparse
import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from time import monotonic, sleep
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


FIXTURES = {
    "dispatch": {"quantity": "Packed weight (kg)", "back": "Back to dispatch board",
                 "listing": "Dispatch board", "relation": "Assigned carrier"},
    "workshop": {"quantity": "Required span (cm)", "back": "Return to registry",
                 "listing": "Production registry", "relation": "Assigned station"},
}


def settle(page):
    """Wait for a stable rendered surface, retaining a bounded wait failure."""
    deadline, previous, equal = monotonic() + 8, None, 0
    while monotonic() < deadline:
        busy = page.locator('[aria-busy="true"]').count()
        surface = page.locator("body").aria_snapshot()
        equal = equal + 1 if not busy and surface == previous else 0
        if equal >= 2:
            return
        previous = surface
        sleep(0.05)
    raise RuntimeError("rendered surface did not settle within eight seconds")


def detail(page, spec, *, wait=True):
    if wait:
        settle(page)
    inputs = page.get_by_role("spinbutton", name=spec["quantity"], exact=True)
    relation = page.get_by_role("region", name=spec["relation"], exact=True)
    return {
        "headings": page.locator("h1").all_text_contents(),
        "quantities": inputs.evaluate_all("els => els.map(el => el.value)"),
        "related_values": relation.locator("dd").all_text_contents(),
        "responses": page.get_by_role("status").all_text_contents(),
        "surface": page.locator("body").aria_snapshot(),
    }


def listing(page, fixture, spec):
    back = page.get_by_role("button", name=spec["back"], exact=True)
    if back.count() == 1:
        back.click()
        settle(page)
    if page.get_by_role("heading", name=spec["listing"], exact=True).count() != 1:
        raise RuntimeError("collection cannot be reached through the visible return control")
    if fixture == "workshop":
        # This known fixture's complete category list is evaluator knowledge only.
        for _ in range(30):
            expand = page.get_by_role("button", name=re.compile(r"^Expand "))
            if not expand.count():
                break
            expand.first.click()
            settle(page)
        else:
            raise RuntimeError("category enumeration budget exhausted")
        rows = page.locator("li").filter(has=page.locator("span"))
        values = []
        for row in rows.all():
            controls = row.get_by_role("button", name=re.compile(r"^Open "))
            # Parent category listitems contain several rows and are not records.
            if controls.count() != 1 or row.locator("li").count():
                continue
            name = controls.inner_text()[len("Open "):]
            text = row.locator("span").inner_text()
            match = re.fullmatch(r"Required span: (.*?) cm", text)
            if not match:
                raise RuntimeError("unexpected workshop quantity presentation")
            values.append((name, match.group(1)))
    else:
        values = []
        for row in page.locator("article").all():
            name = row.get_by_role("heading").inner_text()
            text = row.locator("p").filter(has_text=re.compile(r"^Packed weight:")).inner_text()
            match = re.fullmatch(r"Packed weight: (.*?) kg", text)
            if not match:
                raise RuntimeError("unexpected dispatch quantity presentation")
            values.append((name, match.group(1)))
    if not values or len({name for name, _ in values}) != len(values):
        raise RuntimeError("empty or ambiguous evaluator record enumeration")
    return {"records": dict(values), "surface": page.locator("body").aria_snapshot(),
            "scope": "entire disclosed fixture collection after visible expansion"}


def numeric_equal(actual, expected):
    try:
        return Decimal(actual) == Decimal(expected)
    except (InvalidOperation, ValueError):
        return False


def watch(args):
    """Independent bounded rendered-response sampling, not a product witness."""
    fixture = urlsplit(args.url).path.strip("/")
    if fixture not in FIXTURES:
        raise ValueError("this evaluator only supports the disclosed development fixtures")
    result = {"fixture": fixture, "url": args.url, "mode": "watch", "samples": [],
              "boundary": "Independent browser; visible target/value/resource/response only",
              "scope": "Expected response initially absent, later observed with target/value/resource in one DOM read; not persistence or exclusive causality",
              "max_seconds": args.watch_seconds, "max_page_reads": 240,
              "control_actions": 0, "page_read_attempts": 0}
    started = monotonic()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.set_default_timeout(2000)
            for _ in range(240):
                if monotonic() - started >= args.watch_seconds:
                    break
                result["page_read_attempts"] += 1
                try:
                    page.goto(args.url, wait_until="domcontentloaded")
                    # One synchronous DOM evaluation avoids combining locator
                    # reads from different renders. These fixture-specific
                    # visible selectors belong only to the evaluator.
                    observed = page.locator("body").evaluate("""(body, spec) => {
                        const visible = el => el.getClientRects().length > 0;
                        const all = selector => [...body.querySelectorAll(selector)].filter(visible);
                        const label = el => el.getAttribute('aria-label') ||
                            [...(el.labels || [])].map(x => x.innerText.trim()).join(' ');
                        const regions = all('[aria-label]').filter(el => el.getAttribute('aria-label') === spec.relation);
                        return {headings: all('h1').map(el => el.innerText),
                            quantities: all('input[type="number"]').filter(el => label(el) === spec.quantity).map(el => el.value),
                            related_values: regions.flatMap(el => [...el.querySelectorAll('dd')].filter(visible).map(el => el.innerText)),
                            responses: all('[role="status"]').map(el => el.innerText), surface: body.innerText};
                    }""", FIXTURES[fixture])
                except Exception as exc:
                    result["samples"].append({"seconds": monotonic() - started,
                                              "error": f"{type(exc).__name__}: {exc}"})
                    result["verdict"] = "EVALUATOR_FAILURE"
                    break
                checks = {
                    "target": observed["headings"] == [args.target],
                    "quantity": len(observed["quantities"]) == 1 and numeric_equal(observed["quantities"][0], args.value),
                    "related": bool(observed["related_values"]) and observed["related_values"][0] == args.related,
                    "response": args.expected_response in observed["responses"],
                }
                result["samples"].append({"seconds": monotonic() - started,
                                          "observed": observed, "checks": checks})
                if len(result["samples"]) == 1:
                    print(json.dumps({"watch_ready": True, "initial_checks": checks}), flush=True)
                    if checks["response"]:
                        result["verdict"] = "UNESTABLISHED_INITIAL_RESPONSE_PRESENT"
                        break
                elif all(checks.values()):
                    result.update(verdict="PASS", checks=checks)
                    break
                sleep(0.05)
        finally:
            try:
                browser.close()
            except Exception as exc:
                result.update(verdict="EVALUATOR_FAILURE", cleanup_error=f"{type(exc).__name__}: {exc}")
    result.setdefault("verdict", "UNESTABLISHED_NOT_OBSERVED")
    result["page_reads"] = sum("observed" in sample for sample in result["samples"])
    result["elapsed_seconds"] = monotonic() - started
    return result


def evaluate(args):
    fixture = urlsplit(args.url).path.strip("/")
    if fixture not in FIXTURES:
        raise ValueError("this evaluator only supports the disclosed development fixtures")
    spec = FIXTURES[fixture]
    result = {"fixture": fixture, "url": args.url, "target": args.target,
              "mode": "check" if args.check else "capture", "checks": {},
              "terminal_view": args.terminal_view,
              "boundary": "independent visible DOM evaluation; fixture labels supplied only here",
              "navigation_changes_fixture_view": True}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(args.url, wait_until="networkidle")
            if args.terminal_view == "collection":
                settle(page)
                result["terminal_surface_before_evaluator_actions"] = page.locator("body").aria_snapshot()
                if page.get_by_role("heading", name=spec["listing"], exact=True).count() != 1:
                    raise RuntimeError("operation did not leave the required terminal collection view")
                result["collection"] = listing(page, fixture, spec)
                if not args.check:
                    result["verdict"] = "CAPTURED"
                    return result
                controls = page.get_by_role("button", name="Open " + args.target, exact=True)
                result["checks"]["unique_target_reopen"] = controls.count() == 1
                if controls.count() != 1:
                    result["verdict"] = "FAIL"
                    return result
                controls.click()
                result["detail_evidence_source"] = "evaluator opened the target after capturing terminal collection"
                result["immediate"] = detail(page, spec)
                page.reload(wait_until="networkidle")
                result["reloaded"] = detail(page, spec)
            else:
                result["immediate"] = detail(page, spec)
                page.reload(wait_until="networkidle")
                result["reloaded"] = detail(page, spec)
                result["collection"] = listing(page, fixture, spec)
            if args.check:
                checks = result["checks"]
                for phase in ("immediate", "reloaded"):
                    observed = result[phase]
                    checks[phase + "_target"] = observed["headings"] == [args.target]
                    checks[phase + "_quantity"] = len(observed["quantities"]) == 1 and numeric_equal(
                        observed["quantities"][0], args.value)
                    if args.related is not None:
                        checks[phase + "_related"] = bool(observed["related_values"]) and observed["related_values"][0] == args.related
                    if args.expected_response is not None:
                        checks[phase + "_response"] = args.expected_response in observed["responses"]
                records = result["collection"]["records"]
                checks["collection_target_quantity"] = args.target in records and numeric_equal(records[args.target], args.value)
                if args.baseline:
                    baseline = json.loads(args.baseline.read_text())["collection"]["records"]
                    checks["collection_membership_unchanged"] = records.keys() == baseline.keys()
                    checks["sibling_quantities_unchanged"] = all(
                        name in records and numeric_equal(records[name], value)
                        for name, value in baseline.items() if name != args.target)
                else:
                    result["sibling_check"] = "UNESTABLISHED: no baseline supplied"
                if args.terminal_view == "collection":
                    result["reopened"] = result["reloaded"]
                else:
                    controls = page.get_by_role("button", name="Open " + args.target, exact=True)
                    checks["unique_target_reopen"] = controls.count() == 1
                    if controls.count() == 1:
                        controls.click()
                        result["reopened"] = detail(page, spec)
                if "reopened" in result:
                    observed = result["reopened"]
                    checks["reopened_target_quantity"] = observed["headings"] == [args.target] and len(observed["quantities"]) == 1 and numeric_equal(observed["quantities"][0], args.value)
                result["verdict"] = "PASS" if checks and all(checks.values()) else "FAIL"
            else:
                result["verdict"] = "CAPTURED"
        finally:
            browser.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--capture", action="store_true")
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--watch", action="store_true")
    parser.add_argument("--url", required=True)
    parser.add_argument("--target")
    parser.add_argument("--value")
    parser.add_argument("--related")
    parser.add_argument("--expected-response")
    parser.add_argument("--watch-seconds", type=float, default=45)
    parser.add_argument("--terminal-view", choices=("detail", "collection"), default="detail",
                        help="Collection mode captures rows first, then opens/reloads the target; no relation/response claim")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.check and (args.target is None or args.value is None):
        parser.error("--check requires --target and --value")
    if args.watch and (any(value is None for value in (args.target, args.value, args.related, args.expected_response))
                       or not 0 < args.watch_seconds <= 120):
        parser.error("--watch requires target, value, related, expected-response and 0 < watch-seconds <= 120")
    if args.terminal_view == "collection" and (args.related is not None or args.expected_response is not None):
        parser.error("collection mode cannot check --related or --expected-response: opening the target resets them")
    if args.output.exists():
        parser.error("output already exists; choose a new evidence file")
    try:
        result = watch(args) if args.watch else evaluate(args)
    except Exception as exc:
        result = {"verdict": "EVALUATOR_FAILURE", "error": f"{type(exc).__name__}: {exc}"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps({"verdict": result["verdict"], "output": str(args.output),
                      "checks": result.get("checks"), "error": result.get("error")}))
    return 0 if result["verdict"] in {"PASS", "CAPTURED"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
