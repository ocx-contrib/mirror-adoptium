# NOTICE

This repository packages and redistributes upstream software published by the
[Eclipse Adoptium](https://adoptium.net) Working Group. The Apache-2.0 license
in [`LICENSE`](LICENSE) covers the OCX pipeline files authored here. It does
**not** cover any upstream-derived asset — each package's redistributed bytes
carry their own license, recorded below.

Each package's logo is reproduced for catalog identification only, under
nominative fair use. The marks remain the property of their respective owners
and no endorsement is implied.

| Package | GHCR path | Upstream SPDX |
|---|---|---|
| `temurin` | `ghcr.io/ocx-contrib/adoptium/temurin` | `GPL-2.0-only WITH Classpath-exception-2.0` |

---

## `temurin`

Upstream: <https://github.com/adoptium>
Published to `ghcr.io/ocx-contrib/adoptium/temurin`.

| Component | SPDX | Holder |
|---|---|---|
| Eclipse Temurin (OpenJDK build) | **GPL-2.0-only WITH Classpath-exception-2.0** | Eclipse Foundation / Oracle and the OpenJDK contributors |

"Eclipse", "Adoptium" and "Temurin" are trademarks of the Eclipse Foundation.

No modifications are made to the upstream artifacts; they are republished
byte-for-byte inside an OCX bundle.

### Corresponding Source (GPLv2 with Classpath Exception)

Every Temurin release publishes its own **source archive** alongside the
binaries — `OpenJDK<major>U-jdk-sources_<version>.tar.gz`, served from the same
GitHub release as the artifacts this mirror republishes. That archive is the
complete Corresponding Source for the exact build, including the build scripts.
It is reachable per version from the Adoptium API without a token:

```bash
# Source archive for the build behind OCX version 21.0.12_01001
# (upstream release jdk-21.0.12.1+1):
curl -s -H 'User-Agent: ocx' \
  'https://api.adoptium.net/v3/assets/feature_releases/21/ga?vendor=eclipse&page_size=20' \
  | jq -r '.[] | select(.release_name=="jdk-21.0.12.1+1")
           | .binaries[] | select(.image_type=="sources") | .package.link'
```

Map an OCX version back to its upstream release name with the version-scheme
table in [`temurin/CATALOG.md`](temurin/CATALOG.md); e.g. `21.0.12_01001` →
`jdk-21.0.12.1+1`.

The same source is also reachable from the per-major upstream repositories, at
the matching git tag:

- JDK 8  → <https://github.com/adoptium/jdk8u>
- JDK 11 → <https://github.com/adoptium/jdk11u>
- JDK 17 → <https://github.com/adoptium/jdk17u>
- JDK 21 → <https://github.com/adoptium/jdk21u>
- JDK 25 → <https://github.com/adoptium/jdk25u>
- JDK 26 → <https://github.com/adoptium/jdk26u>

This list must name **every** major in `MAJORS`
([`temurin/scripts/generate.py`](temurin/scripts/generate.py)) — conveying a
GPLv2 binary without its Corresponding Source pointer is the compliance gap, so
adding a major there means adding it here in the same commit.

The Classpath Exception relaxes linking terms only; the source-conveyance duty
is unchanged. Temurin is GPLv2-**only**, so the GPLv3 §6(d) "same place"
option is not available to it — the per-version source archive above is the
§3(a) accompaniment. As required by GPLv2 §3(b), the maintainers of this mirror
additionally offer, valid for three years from the distribution of any given
version, to provide the complete Corresponding Source for that version on
request — open an issue at <https://github.com/ocx-contrib/mirror-adoptium>. No
additional restrictions are imposed beyond the upstream license.
