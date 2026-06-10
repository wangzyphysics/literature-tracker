#!/usr/bin/env python3
"""Stdlib-only test runner (no pytest needed locally).

Discovers test_*.py modules and runs every top-level `test_*` function that
takes no required arguments. Tests MUST avoid pytest fixtures (monkeypatch,
tmp_path); use unittest.mock + tempfile instead so they run both here and
under pytest in CI.

Usage:
  python3 run_tests.py                 # run all test_*.py
  python3 run_tests.py test_foo.py ... # run specific modules
"""
import sys, os, glob, importlib, inspect, traceback

def _runnable(fn):
    try:
        sig = inspect.signature(fn)
    except (ValueError, TypeError):
        return False
    return all(p.default is not inspect.Parameter.empty
               or p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
               for p in sig.parameters.values())

def main(argv):
    mods = argv or sorted(glob.glob("test_*.py"))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    passed = failed = skipped = 0
    failures = []
    for path in mods:
        name = os.path.splitext(os.path.basename(path))[0]
        try:
            mod = importlib.import_module(name)
        except ModuleNotFoundError as e:
            missing = (e.name or "").split(".")[0]
            here = os.path.dirname(os.path.abspath(__file__))
            if missing and not os.path.exists(os.path.join(here, missing + ".py")):
                # 第三方依赖本机未装(本地无 pip):降级为 skip,CI(装全依赖)仍全量执行
                skipped += 1
                print(f"⊘ {name} (missing optional dep: {missing} — skipped locally)")
                continue
            failures.append((name, "<import>", traceback.format_exc()))
            failed += 1
            print(f"✗ {name}: import error: {e}")
            continue
        except Exception as e:
            failures.append((name, "<import>", traceback.format_exc()))
            failed += 1
            print(f"✗ {name}: import error: {e}")
            continue
        for attr in sorted(dir(mod)):
            if not attr.startswith("test_"):
                continue
            fn = getattr(mod, attr)
            if not callable(fn):
                continue
            if not _runnable(fn):
                skipped += 1
                print(f"⊘ {name}.{attr} (needs fixture — skipped locally)")
                continue
            try:
                fn()
                passed += 1
                print(f"✓ {name}.{attr}")
            except Exception as e:
                failed += 1
                failures.append((name, attr, traceback.format_exc()))
                print(f"✗ {name}.{attr}: {e}")
    print(f"\n{passed} passed, {failed} failed, {skipped} skipped")
    if failures:
        print("\n=== FAILURES ===")
        for name, attr, tb in failures:
            print(f"\n--- {name}.{attr} ---\n{tb}")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
