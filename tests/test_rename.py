"""M0b: the keyword-package layout. Old names must keep working; new paths must expose the same objects."""
import importlib
import inspect
import pkgutil
import re
from pathlib import Path

import sufd
from sufd.glossary import GLOSSARY

ROOT = Path(__file__).resolve().parent.parent
PKGS = ["eno", "emem", "idea", "akpaneka", "kufre", "edimek"]

NEW_TO_OLD = {
    "EnoSignal": "Signal", "IdeaEnvelope": "Envelope", "EdimekLens": "Lens", "edimek_choose_lens": "choose_lens",
    "edimek_render_svg": "render_svg", "AkpanekaNote": "Note", "AkpanekaFollower": "Follower",
    "AkpanekaWatch": "Watch", "EdimekFollow": "Follow", "KufreMind": "Mind", "KufreProbe": "SelfProbe",
}


def test_every_new_name_is_the_same_object_as_its_slice1_alias():
    for new, old in NEW_TO_OLD.items():
        assert getattr(sufd, new) is getattr(sufd, old), (new, old)


def test_new_paths_expose_the_public_names():
    assert importlib.import_module("sufd.eno").EnoSignal is sufd.Signal
    assert importlib.import_module("sufd.idea").IdeaEnvelope is sufd.Envelope
    assert importlib.import_module("sufd.akpaneka").AkpanekaWatch is sufd.Watch
    assert importlib.import_module("sufd.kufre").KufreSense is importlib.import_module("sufd.selfmodel").SenseRecord
    edimek = importlib.import_module("sufd.edimek")
    assert edimek.EdimekAxis is importlib.import_module("sufd.lens").Axis
    assert edimek.edimek_explain.__name__ == "edimek_explain"


def test_old_module_paths_still_import():
    for mod, names in {"sufd.signal": ["Signal"], "sufd.envelope": ["Envelope", "WARMUP"],
                       "sufd.lens": ["Lens", "Axis", "choose_lens", "nice_ticks", "decimate_minmax"],
                       "sufd.render": ["render_svg"], "sufd.follow": ["Note", "Follower", "Watch", "Follow"],
                       "sufd.selfmodel": ["Mind", "SelfProbe", "SenseRecord", "NEEDS"]}.items():
        m = importlib.import_module(mod)
        for n in names:
            assert hasattr(m, n), (mod, n)


def test_every_module_in_a_keyword_package_states_its_role_first():
    for pkg in PKGS:
        mod = importlib.import_module(f"sufd.{pkg}")
        names = [pkg] + [f"{pkg}.{m.name}" for m in pkgutil.iter_modules(mod.__path__)]
        for n in names:
            doc = importlib.import_module(f"sufd.{n}").__doc__ or ""
            assert doc.startswith(f"{pkg} — {GLOSSARY[pkg]}"), (n, doc[:60])


def test_public_classes_carry_their_package_keyword():
    for pkg in PKGS:
        mod = importlib.import_module(f"sufd.{pkg}")
        for name in getattr(mod, "__all__", []):
            obj = getattr(mod, name)
            if inspect.isclass(obj) or inspect.isfunction(obj):      # type aliases (Sample, Value) are exempt
                assert name.lower().startswith(pkg), (pkg, name)


def test_glossary_matches_the_knowledge_base():
    kb = (ROOT / "spec" / "knowledge-base.md").read_text(encoding="utf-8")
    for pkg, role in GLOSSARY.items():
        row = next(l for l in kb.splitlines() if l.startswith(f"| `{pkg}/`"))
        first = role.split()[0]
        assert first in row, (pkg, role, row)
    assert set(GLOSSARY) == set(PKGS)


def test_no_import_cycle_at_load():
    for pkg in PKGS:
        importlib.reload(importlib.import_module(f"sufd.{pkg}"))
