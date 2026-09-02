# /// script
# requires-python = ">=3.13"
# dependencies = ["ocx-mirror-sdk~=0.6.0"]
# ///
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 The OCX Authors
"""Generate url_index JSON for Eclipse Temurin.

One generator drives every mirrored JDK major (8, 11, 17, 21, 25, 26). Each
major has its own upstream release repository (`adoptium/temurin<major>-binaries`)
and its own tag space, so a `github_release` source would need one spec per
major. The Adoptium API aggregates them, hands back an already-parsed
`version_data` block, and names the JDK *and* JRE archives of a release in one
response — so a single `url_index` covers the whole matrix.

Both image types this mirror publishes (`jdk` and `jre`) are emitted into the
same version's asset map; `mirror.yml`'s two `variants:` route each to its own
tag prefix (`21.0.12_01001` and `jre-21.0.12_01001`).

Per-major floors live in ``MAJOR_FLOORS`` so a fresh mirror does not bootstrap
every GA patch back to each major's first release. Bump them to retire older
patches.

Cascade safety: each major's version space is disjoint (an `8.x` version never
collides with a `21.x`), and the OCX version always carries the JDK major as
its leading component. Cascade tags (`X.Y.Z → X.Y → X → latest`) are therefore
per-major-safe: `temurin:8`, `temurin:21`, … never alias one another, and
`temurin:latest` tracks the highest JDK major.

═══ VERSION SCHEME — the part that must be right ═══════════════════════════

    jdk-21.0.12.1+1  ->  21.0.12_01001
    jdk-21.0.12+8    ->  21.0.12_00008
    jdk8u504-b01     ->  8.0.504_00001

    ocx = f"{major}.{minor}.{security}_{patch:02d}{build:03d}"

OCX build metadata is compared as a **STRING**, never as a number
(`ocx_lib/src/package/version.rs`, `lhs_build.cmp(rhs_build)`), and cascade
blocking inherits that ordering. An UNPADDED numeric token therefore
mis-orders: `_10001` sorts BELOW `_8001`, the higher build is treated as older,
and the rolling alias never repoints. That is live today on
`ghcr.io/ocx-contrib/amazon/corretto` — `:17` and `:17.0.20` serve the older
August build — and `ocx package cascade check` reports it as "ok", because the
fold uses the same comparator that produced the tags. Filed as ocx-sh/ocx#396.

FIXED WIDTH is the whole defence: padded digits make lexicographic order equal
numeric order. `_ceiling_check` below asserts the widths hold, and fails the
generator rather than emitting a version that would silently mis-order.

`patch` leads the token because it outranks `build` upstream: `21.0.12.1+1`
(patch 1, build 1) really is newer than `21.0.12+8` (no patch, build 8).
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

from ocx_mirror_sdk import IndexBuilder

API = "https://api.adoptium.net/v3"

# The API answers 403 to a request with no User-Agent.
UA = "ocx-mirror/mirror-adoptium (+https://github.com/ocx-contrib/mirror-adoptium)"

# Mirrored majors: every LTS line plus the current feature release.
MAJORS: tuple[int, ...] = (8, 11, 17, 21, 25, 26)

# Per-major floor as the normalized 5-tuple (major, minor, security, patch,
# build) — INCLUSIVE. Set to the 4th-newest GA of each major at bootstrap
# (2026-09-02) so a fresh mirror backfills a security-patch line without
# pulling years of history. Bump these to retire older patches.
MAJOR_FLOORS: dict[int, tuple[int, int, int, int, int]] = {
    8: (8, 0, 482, 0, 8),    # jdk8u482-b08
    11: (11, 0, 30, 0, 7),   # jdk-11.0.30+7
    17: (17, 0, 18, 0, 8),   # jdk-17.0.18+8
    21: (21, 0, 10, 0, 7),   # jdk-21.0.10+7
    25: (25, 0, 2, 0, 10),   # jdk-25.0.2+10
    26: (26, 0, 0, 0, 35),   # jdk-26+35
}

# Image types this mirror publishes, one per `variants:` entry in mirror.yml.
# Everything else upstream ships under the same release (`debugimage`,
# `testimage`, `staticlibs`, `sbom`, `sources`) is out of scope — `sources` is
# still named in NOTICE.md as the Corresponding Source pointer GPLv2 requires.
IMAGE_TYPES = frozenset({"jdk", "jre"})

# Upstream (os, architecture) pairs that map onto an OCX platform key. The
# mapping itself lives in mirror.yml's asset regexes; this set is the scope
# gate. Deliberately excluded, because OCX has no key for them:
# linux/arm (32-bit), linux/ppc64le, linux/s390x, linux/riscv64, aix/ppc64,
# solaris/*. windows/aarch64 is excluded for a different reason — see the
# `windows/arm64` comment in ../mirror-base.yml.
SCOPE = frozenset(
    {
        ("linux", "x64"),
        ("linux", "aarch64"),
        ("alpine-linux", "x64"),
        ("alpine-linux", "aarch64"),
        ("mac", "x64"),
        ("mac", "aarch64"),
        ("windows", "x64"),
    }
)

# Coverage is genuinely ragged upstream and that is not an error: JDK 8 ships
# no mac/aarch64, and alpine-linux/aarch64 starts at 21. A version simply
# publishes the platforms it has. This table is what the run LOGS so a
# newly-missing platform is visible rather than silent — `0 matches` on an
# asset regex is skipped without comment by the pipeline.
EXPECTED_ABSENT: dict[int, frozenset[tuple[str, str]]] = {
    8: frozenset({("mac", "aarch64"), ("alpine-linux", "aarch64")}),
    11: frozenset({("alpine-linux", "aarch64")}),
    17: frozenset({("alpine-linux", "aarch64")}),
    21: frozenset(),
    25: frozenset(),
    26: frozenset(),
}


def log(msg: str) -> None:
    print(msg, file=sys.stderr)


def get(path: str) -> list:
    req = urllib.request.Request(f"{API}{path}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.load(resp)


def normalize(version_data: dict) -> tuple[int, int, int, int, int]:
    """Upstream `version_data` -> the 5-tuple the floor and the tag are built from.

    `patch` is absent on most releases (only a respin carries one) and is 0
    there; `minor` is 0 for every Temurin release to date but is read, not
    assumed.
    """
    return (
        int(version_data["major"]),
        int(version_data.get("minor") or 0),
        int(version_data.get("security") or 0),
        int(version_data.get("patch") or 0),
        int(version_data["build"]),
    )


def _ceiling_check(major: int, patch: int, build: int) -> None:
    """Fail loudly rather than emit a token whose width breaks the ordering.

    The padding is the ONLY thing making the string comparison agree with
    numeric order. A 3-digit patch or a 4-digit build would widen the token and
    reintroduce exactly the corretto defect this scheme exists to avoid.
    """
    if not 0 <= patch <= 99:
        raise SystemExit(
            f"JDK {major}: patch {patch} exceeds the 2-digit build-token field. "
            "Widen the padding in ocx_version() AND re-mirror every published "
            "version of this major — a mixed-width token mis-orders."
        )
    if not 0 <= build <= 999:
        raise SystemExit(
            f"JDK {major}: build {build} exceeds the 3-digit build-token field. "
            "Widen the padding in ocx_version() AND re-mirror every published "
            "version of this major — a mixed-width token mis-orders."
        )


def ocx_version(nums: tuple[int, int, int, int, int]) -> str:
    major, minor, security, patch, build = nums
    _ceiling_check(major, patch, build)
    return f"{major}.{minor}.{security}_{patch:02d}{build:03d}"


def collect(major: int) -> list[dict]:
    """Every GA release of one major, newest first, down to its floor."""
    floor = MAJOR_FLOORS[major]
    out: list[dict] = []
    page = 0
    while page < 10:  # 10 x 20 releases is far past any floor set here
        try:
            batch = get(
                f"/assets/feature_releases/{major}/ga"
                f"?vendor=eclipse&page_size=20&page={page}"
            )
        except urllib.error.HTTPError as exc:
            if exc.code == 404:  # past the last page
                break
            raise
        if not batch:
            break
        below_floor = False
        for release in batch:
            if normalize(release["version_data"]) < floor:
                below_floor = True
                continue
            out.append(release)
        if below_floor:
            break
        page += 1
    return out


def main() -> int:
    index = IndexBuilder()
    emitted = 0

    for major in MAJORS:
        releases = collect(major)
        log(f"JDK {major}: {len(releases)} GA releases at or above the floor")

        for release in releases:
            nums = normalize(release["version_data"])
            version = ocx_version(nums)

            assets: dict[str, str] = {}
            present: set[tuple[str, str]] = set()
            for binary in release["binaries"]:
                if binary["image_type"] not in IMAGE_TYPES:
                    continue
                key = (binary["os"], binary["architecture"])
                if key not in SCOPE:
                    continue
                package = binary["package"]
                assets[package["name"]] = package["link"]
                present.add(key)

            if not assets:
                log(f"  skip {release['release_name']} -> {version} (no in-scope assets)")
                continue

            # A platform whose asset regex matches nothing is skipped silently
            # by the pipeline, so an upstream that quietly stops shipping one
            # would go unnoticed. Name it here instead.
            missing = SCOPE - present - EXPECTED_ABSENT[major]
            if missing:
                log(
                    f"  WARNING {release['release_name']} -> {version}: "
                    f"unexpected missing platforms {sorted(missing)}"
                )

            index.add_version(version, assets=assets, prerelease=False)
            log(f"  {release['release_name']} -> {version} ({len(assets)} assets)")
            emitted += 1

    if emitted == 0:
        log("no versions generated — check MAJOR_FLOORS against upstream")
        return 1

    index.emit()
    log(f"done — {emitted} versions total")
    return 0


def self_check() -> int:
    """Assert the version scheme against real upstream release shapes.

    Run with `uv run scripts/generate.py --self-check`. Guards the property
    that silently mis-publishes rather than reds: build-token ordering.
    """
    # (release_name, version_data, expected ocx version)
    cases = [
        ("jdk-21.0.12.1+1", {"major": 21, "minor": 0, "security": 12, "patch": 1, "build": 1}, "21.0.12_01001"),
        ("jdk-21.0.12+8", {"major": 21, "minor": 0, "security": 12, "build": 8}, "21.0.12_00008"),
        ("jdk-21.0.11+10", {"major": 21, "minor": 0, "security": 11, "build": 10}, "21.0.11_00010"),
        ("jdk8u504-b01", {"major": 8, "minor": 0, "security": 504, "build": 1}, "8.0.504_00001"),
        ("jdk-26+35", {"major": 26, "minor": 0, "security": 0, "build": 35}, "26.0.0_00035"),
        ("jdk-25.0.4.1+1", {"major": 25, "minor": 0, "security": 4, "patch": 1, "build": 1}, "25.0.4_01001"),
    ]
    failed = 0
    for name, vd, want in cases:
        got = ocx_version(normalize(vd))
        status = "ok " if got == want else "FAIL"
        if got != want:
            failed += 1
        log(f"  {status} {name:<18} -> {got} (want {want})")

    # The ordering property itself, asserted the way OCX compares it: as
    # STRINGS. This is what an unpadded token gets wrong.
    ordered = [
        "21.0.11_00010",  # jdk-21.0.11+10
        "21.0.12_00008",  # jdk-21.0.12+8
        "21.0.12_01001",  # jdk-21.0.12.1+1 — a respin of 21.0.12, newer
    ]
    for lo, hi in zip(ordered, ordered[1:]):
        lo_build, hi_build = lo.split("_")[1], hi.split("_")[1]
        if lo.split("_")[0] == hi.split("_")[0] and not lo_build < hi_build:
            log(f"  FAIL string order: {lo!r} must sort below {hi!r}")
            failed += 1
        else:
            log(f"  ok  order {lo} < {hi}")

    # The ceilings the padding depends on.
    for patch, build in ((100, 1), (0, 1000)):
        try:
            ocx_version((21, 0, 12, patch, build))
        except SystemExit:
            log(f"  ok  ceiling rejected patch={patch} build={build}")
        else:
            log(f"  FAIL ceiling accepted patch={patch} build={build}")
            failed += 1

    log("self-check FAILED" if failed else "self-check passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_check() if "--self-check" in sys.argv else main())
