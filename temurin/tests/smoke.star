# tests/smoke.star — one script for both variants (jdk, jre) and every
# mirrored major (8, 11, 17, 21, 25, 26).
#
# Asserts the contract — exit code, version SHAPE, a computed cryptographic
# result, self-location after relocation — never vendor prose ("Temurin",
# "OpenJDK", "Eclipse"). A rebrand must not red this file.
#
# DIALECT: Bazel .bzl. A top-level `if`/`for` STATEMENT is a parse error that
# reds every version on every platform at once. Module scope uses ternary
# EXPRESSIONS only; real branching lives inside a `def` called from the bottom.

IS_WIN = ocx.target_platform.os == ocx.os.Windows

EXE = ".exe" if IS_WIN else ""
JAVA = "java" + EXE
JAVAC = "javac" + EXE
KEYTOOL = "keytool" + EXE

# NOTE — the bundle's own files cannot be probed from here, so nothing below
# reads one. Measured against ocx 0.6.0 on a real bundle (both spellings fail):
#
#   ocx.exists("bin/javac")            -> False, even though bin/javac IS in
#                                         the bundle (resolves scratch-only)
#   ocx.exists(ocx.package_root + "/bin/javac")
#                                      -> script error, "path escapes the sandbox"
#   ocx.read_file("release")           -> script error, "No such file or directory"
#
# `ocx.run` on an absent binary is likewise a SPAWN error, not a non-zero exit
# ("failed to spawn 'javac'"), so it cannot be used as a probe either — the
# script cannot catch it. Every check below therefore goes through a binary
# both variants ship.
# ── Tier 1 + 2: liveness and version SHAPE ─────────────────────────────────
# The JVM prints `-version` to stderr. Digits are the contract: JDK 8 prints
# `1.8.0_NNN`, 11+ print `11.0.x` … `26.0.x`. Both satisfy \d+\.\d+\.\d+.
# `--version` is NOT used: JDK 8 does not have it.
r_version = ocx.run(JAVA, "-version")
expect.ok(r_version)
expect.matches(r_version.stdout + r_version.stderr, r"\d+\.\d+\.\d+")

# ── Tier 3: a computed result, on input we write ourselves ─────────────────
# `keytool` is in BOTH the JDK and the JRE bin set on every mirrored major, so
# this is the functional check the two variants share. It generates a real RSA
# keypair, writes a PKCS12 store, and reads it back — exercising the crypto
# providers and lib/ resources, not just the launcher. The asserted token is
# the alias this script chose, never upstream text.
ocx.run(
    KEYTOOL,
    "-genkeypair",
    "-alias", "ocxsmoke",
    "-keyalg", "RSA",
    "-keysize", "2048",
    "-dname", "CN=ocx-smoke",
    "-validity", "1",
    "-keystore", "smoke.p12",
    "-storetype", "PKCS12",
    "-storepass", "changeit",
    "-keypass", "changeit",
)
expect.true(ocx.exists("smoke.p12"), msg="keytool did not write the keystore")

r_list = ocx.run(KEYTOOL, "-list", "-keystore", "smoke.p12", "-storepass", "changeit")
expect.ok(r_list)
expect.contains(r_list.stdout, "ocxsmoke")

# ── Tier 4: the relocated runtime self-locates ─────────────────────────────
# `java.home` (reported to stderr) must resolve to a real path, proving
# bin/java finds its sibling lib/ after the bundle is relocated into the
# install tree.
#
# NOTE: metadata.json wires JAVA_HOME as a `constant` var with
# `visibility: public`, so it IS exported to consumers — but `ocx package test`
# composes only `path`-type vars, so it is not visible inside this sandbox and
# is deliberately not asserted here. This check is the functional equivalent.
r_props = ocx.run(JAVA, "-XshowSettings:properties", "-version")
expect.ok(r_props)
expect.matches(r_props.stdout + r_props.stderr, r"java\.home = \S+")


# ── Which flavour is in this bundle ────────────────────────────────────────
# The module list is the only flavour signal reachable through a binary both
# variants ship: a JDK image contains `jdk.compiler`, a JRE image does not.
# JDK 8 predates modules and exits non-zero on `--list-modules` (an ordinary
# non-zero exit — `java` itself spawns fine), which is why this is not
# `expect.ok`'d.
r_modules = ocx.run(JAVA, "--list-modules")
HAS_MODULES = r_modules.exit_code == 0
IS_JDK = HAS_MODULES and r_modules.stdout.find("jdk.compiler") >= 0


def check_module_image_is_coherent():
    """The module image, where there is one, must be internally consistent."""
    if HAS_MODULES:
        # Every Java image since 9 contains java.base; an image without it is
        # a truncated archive, not a JRE.
        expect.contains(r_modules.stdout, "java.base")


def check_compiler_actually_compiles():
    """On a JDK bundle, exercise the compiler on input we write ourselves.

    Skipped on a JRE (no compiler by definition) and on JDK 8, whose image
    carries no module list to detect the compiler from — 8 still gets every
    tier above. This is the one check that would red on a JDK image whose
    `bin/` arrived truncated.
    """
    if IS_JDK:
        ocx.write_file(
            "Smoke.java",
            "public class Smoke { public static void main(String[] a) { System.out.println(6 * 7); } }\n",
        )
        r_javac = ocx.run(JAVAC, "Smoke.java")
        expect.ok(r_javac)
        r_run = ocx.run(JAVA, "Smoke")
        expect.ok(r_run)
        expect.contains(r_run.stdout, "42")


check_module_image_is_coherent()
check_compiler_actually_compiles()
