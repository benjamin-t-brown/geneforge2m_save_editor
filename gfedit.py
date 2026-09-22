#!/usr/bin/env python3
"""Geneforge 2: Infestation save editor.

Usage:
  python gfedit.py show    --slot 1
  python gfedit.py heal    --slot 1
  python gfedit.py set     --slot 1 Stealth=8 HealthCur=100
  python gfedit.py restore --slot 1
  python gfedit.py list

The slot must be given explicitly -- there is no default.

  --slot N          the save DIRECTORY number, i.e. SaveN/
  --ingame-slot N   the slot number shown in the game menu (= --slot N-1)

Save dirs are zero-indexed, so the game's "slot 2" is Save1/ == --slot 1.
Every write makes a .bak first. Quit the game before editing.
"""
import argparse, os, sys, shutil, struct

SAVEDIR = "Geneforge 2 Infestation Saved Games"
ROOT = None   # resolved lazily so --help works without the game installed

NUL = b"\x00"

SKILLS = {
    "Strength": 0xf77c, "Agility": 0xf77e, "Intellect": 0xf780,
    "EssenceMastery": 0xf782, "Endurance": 0xf784,
    "Melee": 0xf788, "Missile": 0xf78a, "QuickAction": 0xf78c, "Evasion": 0xf78e,
    "BattleMagic": 0xf792, "MentalMagic": 0xf794,
    "BlessingMagic": 0xf796, "Spellcraft": 0xf798,
    "FireShaping": 0xf79c, "BattleShaping": 0xf79e,
    "MagicShaping": 0xf7a0, "HealingCraft": 0xf7a2,
    "Leadership": 0xf7a6, "Mechanics": 0xf7a8, "Stealth": 0xf7aa,
}
# Pools are stored as three int16 slots: [current, max, current_mirror].
# Derived from essence 13/44 -> (13, 44, 13); health/energy were full so flat.
POOLS = {
    "Health":  {"cur": (0xf6f2, 0xf6f6), "max": 0xf6f4},
    "Energy":  {"cur": (0xf6f8, 0xf6fc), "max": 0xf6fa},
    "Essence": {"cur": (0xf6fe, 0xf702), "max": 0xf700},
}
VITALS = {"Level": (0xf6ee, 2), "XP": (0x10014, 4)}
MAXV = 250   # refuse absurd values; the UI and combat math get weird past this


def find_root():
    """Locate the save folder: $GF2_SAVES, next to this script, or the default."""
    env = os.environ.get("GF2_SAVES")
    if env:
        return env
    here = os.path.dirname(os.path.abspath(__file__))
    cands = [
        os.path.join(here, SAVEDIR),
        os.path.join(os.path.expanduser("~"), "Documents", "Spiderweb Software", SAVEDIR),
    ]
    for c in cands:
        if os.path.isdir(c):
            return c
    return cands[-1]


def root():
    global ROOT
    if ROOT is None:
        ROOT = find_root()
    return ROOT


def path(slot):
    p = os.path.join(root(), "Save%d" % slot, "data")
    if not os.path.exists(p):
        sys.exit("no save at %s\n(try: gfedit.py list)" % p)
    return p


def show(slot):
    d = open(path(slot), "rb").read()
    g = lambda o, w=2: struct.unpack_from("<h" if w == 2 else "<i", d, o)[0]
    print("== Save%d (game slot %d) ==" % (slot, slot + 1))
    for k, (o, w) in VITALS.items():
        print("  %-14s %d" % (k, g(o, w)))
    for k, spec in POOLS.items():
        print("  %-14s %d/%d" % (k, g(spec["cur"][0]), g(spec["max"])))
    print("  -- skills (invested points; sheet adds bonuses) --")
    for k, o in SKILLS.items():
        print("  %-14s %3d   @%s" % (k, g(o), hex(o)))


def setvals(slot, pairs):
    p = path(slot)
    shutil.copy2(p, p + ".bak")
    d = bytearray(open(p, "rb").read())
    n = len(d)
    for pair in pairs:
        if "=" not in pair:
            sys.exit("bad arg %r, want Name=Value" % pair)
        k, v = pair.split("=", 1)
        v = int(v)
        if k in SKILLS:
            if not 0 <= v <= MAXV:
                sys.exit("%s=%d out of range 0..%d" % (k, v, MAXV))
            struct.pack_into("<h", d, SKILLS[k], v)
        elif k.endswith("Cur") and k[:-3] in POOLS:
            for o in POOLS[k[:-3]]["cur"]:
                struct.pack_into("<h", d, o, v)
        elif k.endswith("Max") and k[:-3] in POOLS:
            struct.pack_into("<h", d, POOLS[k[:-3]]["max"], v)
        elif k in VITALS:
            o, w = VITALS[k]
            struct.pack_into("<h" if w == 2 else "<i", d, o, v)
        else:
            sys.exit("unknown field %r" % k)
        print("  set %-14s = %d" % (k, v))
    assert len(d) == n, "length changed -- refusing to write"
    open(p, "wb").write(d)
    print("wrote %s (backup at %s.bak)" % (p, os.path.basename(p)))


def heal(slot):
    """Fill every pool to its current max, reading maxes from the file."""
    p = path(slot)
    shutil.copy2(p, p + ".bak")
    d = bytearray(open(p, "rb").read())
    n = len(d)
    for name, spec in POOLS.items():
        mx = struct.unpack_from("<h", d, spec["max"])[0]
        cur = struct.unpack_from("<h", d, spec["cur"][0])[0]
        for o in spec["cur"]:
            struct.pack_into("<h", d, o, mx)
        print("  %-8s %d -> %d/%d" % (name, cur, mx, mx))
    assert len(d) == n, "length changed -- refusing to write"
    open(p, "wb").write(d)
    print("wrote %s (backup at %s.bak)" % (p, os.path.basename(p)))


def restore(slot):
    p = path(slot)
    if not os.path.exists(p + ".bak"):
        sys.exit("no backup for slot %d" % slot)
    shutil.copy2(p + ".bak", p)
    print("restored slot %d from backup" % slot)


def list_slots():
    r = root()
    if not os.path.isdir(r):
        sys.exit("no save folder at %s\n(set GF2_SAVES to override)" % r)
    print("saves in %s" % r)
    found = False
    for name in sorted(os.listdir(r)):
        if not name.startswith("Save"):
            continue
        if not os.path.exists(os.path.join(r, name, "data")):
            continue
        found = True
        n = int(name[4:])
        try:
            hdr = open(os.path.join(r, name, "header"), "rb").read(0x40)
            label = hdr[:32].split(NUL)[0].decode("ascii", "replace")
            zone = hdr[0x28:0x40].split(NUL)[0].decode("ascii", "replace")
        except (OSError, ValueError):
            label, zone = "?", "?"
        print("  --slot %-3d (game slot %-3d)  %-24s %s"
              % (n, n + 1, label or "(unnamed)", zone))
    if not found:
        print("  (none)")


def main():
    ap = argparse.ArgumentParser(
        prog="gfedit", description="Geneforge 2: Infestation save editor")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def with_slot(name, help_):
        q = sub.add_parser(name, help=help_)
        g = q.add_mutually_exclusive_group(required=True)
        g.add_argument("--slot", type=int, metavar="N",
                       help="save DIRECTORY number (SaveN)")
        g.add_argument("--ingame-slot", type=int, metavar="N",
                       help="slot number as shown in-game (= --slot N-1)")
        return q

    with_slot("show", "print current values")
    with_slot("heal", "fill all pools to max")
    with_slot("restore", "revert the last write from .bak")
    q = with_slot("set", "patch fields, e.g. Stealth=8")
    q.add_argument("pairs", nargs="+", metavar="Name=Value")
    sub.add_parser("list", help="list save slots on disk")

    a = ap.parse_args()
    if a.cmd == "list":
        return list_slots()

    if a.ingame_slot is not None:
        if a.ingame_slot < 1:
            ap.error("--ingame-slot is 1-based, got %d" % a.ingame_slot)
        slot = a.ingame_slot - 1
    else:
        if a.slot < 0:
            ap.error("--slot must be >= 0")
        slot = a.slot

    if a.cmd == "show":
        show(slot)
    elif a.cmd == "heal":
        heal(slot)
    elif a.cmd == "set":
        setvals(slot, a.pairs)
    elif a.cmd == "restore":
        restore(slot)


if __name__ == "__main__":
    main()
