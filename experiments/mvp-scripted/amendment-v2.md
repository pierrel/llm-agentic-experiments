# Scripted MVP v2 amendment

The package initializer imports `current_assist.py` before executing
`harness.demo`, but the v1 scripted-MVP implementation digest omitted that
imported module. A change there could make the package's execution path differ
without changing the v1 digest.

MVP v2 adds that exact package-initialization dependency to the digest and a
regression test. It deliberately does not hash arbitrary unimported future
modules: an existing hashed import must change before such a module can affect
the scripted runner. The fixture, conditions, script, schedule, tool schemas,
and primary artifact outcome are unchanged. This is a new no-model study
version; v1 remains unchanged.
