# mirror-adoptium

OCX mirrors for [Eclipse Adoptium](https://adoptium.net) runtimes.

| Package | Coordinate | Upstream |
|---|---|---|
| `temurin` | [`ocx.sh/adoptium/temurin`](https://index.ocx.sh/adoptium/temurin) | [adoptium](https://github.com/adoptium) |

Two variants publish from every release: the default (full JDK) and `jre-`
(runtime only) — `adoptium/temurin:21` and `adoptium/temurin:jre-21`.

## Layout

```
temurin/
├── mirror.yml           the spec
├── metadata.json        bundle env (+ metadata-darwin.json for the Contents/Home layout)
├── CATALOG.md           what `ocx package describe` publishes
├── scripts/generate.py  Adoptium API -> url_index
└── tests/smoke.star     smoke test, one script for both variants
mirror-base.yml          repo-wide policy, inherited via `extends:`
```

## Editing

Change the spec, then regenerate CI — **never hand-edit
`.github/workflows/`**, which is generated and guarded by
`verify-generated.yml` (exit 65 on drift):

```bash
direnv allow                                     # once, activates the pinned toolchain
ocx-mirror package validate temurin/mirror.yml
ocx-mirror package pipeline generate ci --spec temurin/mirror.yml
```

Check the generator against upstream release shapes without touching the
network:

```bash
uv run temurin/scripts/generate.py --self-check
```

## Adding a major

`MAJORS` and `MAJOR_FLOORS` in `temurin/scripts/generate.py` are the only gate
on which JDK lines are mirrored. Adding a major there means adding its source
repository to `NOTICE.md` in the same commit — a GPLv2 binary published without
its Corresponding Source pointer is a compliance gap.

## Licence

Mirror pipeline files: Apache-2.0 (`LICENSE`). The redistributed binaries are
OpenJDK under **GPL-2.0 with the Classpath Exception** — see `NOTICE.md` for
attribution and the Corresponding Source pointer.
