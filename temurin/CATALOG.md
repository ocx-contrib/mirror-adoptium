---
title: Eclipse Temurin
description: Free, TCK-tested OpenJDK builds from the Eclipse Adoptium project
keywords: java,jdk,jre,openjdk,temurin,adoptium,runtime
---

# Eclipse Temurin

Eclipse Temurin is the OpenJDK distribution produced by the Eclipse Adoptium
Working Group. Builds are reproducible, TCK-tested for Java SE conformance, and
published at no cost under the same licence as OpenJDK itself, with quarterly
security updates on every supported line.

## What's included

Two variants ship from every release. The **JDK** is the default; the **JRE**
is the same runtime without the development tools.

- **java** — JVM runtime *(both variants)*
- **keytool** — keystore and certificate management *(both variants)*
- **javac** — Java compiler *(JDK only)*
- **jar** — archive tool *(JDK only)*
- **jshell** — interactive REPL *(JDK 11+)*
- **jpackage** — native installer packaging *(JDK 14+)*

## Variants

| Coordinate | Contents | Size |
|---|---|---|
| `adoptium/temurin:21` | full JDK — compiler and dev tools | ~200 MB |
| `adoptium/temurin:jre-21` | runtime only | ~50 MB |

The JRE variant exists for every mirrored major.

## Available versions

- **Temurin 26** — newest; a six-month feature release, not LTS
- **Temurin 25** — LTS
- **Temurin 21** — LTS
- **Temurin 17** — LTS
- **Temurin 11** — LTS
- **Temurin 8** — LTS

`:latest` follows the **highest** major, currently 26. Pin an LTS line
(`:25`, `:21`, `:17`, `:11`, `:8`) if you need one.

## Version scheme

Upstream release names carry more components than an OCX version has slots, so
the trailing two fold into the build segment as `patch × 1000 + build`, each
zero-padded to a fixed width:

    major.minor.security_PPBBB

| Upstream release | OCX version |
|---|---|
| `jdk-21.0.12.1+1` | `21.0.12_01001` |
| `jdk-21.0.12+8` | `21.0.12_00008` |
| `jdk-21.0.11+10` | `21.0.11_00010` |
| `jdk8u504-b01` | `8.0.504_00001` |
| `jdk-26+35` | `26.0.0_00035` |

JDK 8 release names carry no minor or patch component; both are inserted as 0
during conversion. The padding is not cosmetic — OCX compares build metadata as
text, so a variable-width token would sort a higher build below a lower one.

Add the variant prefix for the runtime-only builds: `jre-21.0.12_01001`.

## Platforms

Linux (glibc and musl) on x86-64 and AArch64, macOS on both architectures, and
Windows on x86-64. Upstream also publishes AIX, Solaris, 32-bit ARM, ppc64le,
s390x and RISC-V builds, which OCX has no platform key for.

## Licence

Temurin is OpenJDK, licensed **GPL-2.0 with the Classpath Exception**. The
exception permits linking your own code against the class libraries without the
GPL extending to it. Corresponding Source for every mirrored build, and a
three-year written offer for it, are in the mirror repository's `NOTICE.md`.
The OCX mirror pipeline files are Apache-2.0.
