#!/usr/bin/env python3
"""Geneforge 2: Infestation save editor.

Usage:
  python gfedit.py show 1
  python gfedit.py set 1 Stealth=8 HealthCur=100 HealthMax=200
  python gfedit.py heal 1
  python gfedit.py restore 1

Slot numbers are the DIRECTORY number (in-game "slot 2" == Save1).
Every write makes a .bak first. Quit the game before editing.
"""
import os, sys, shutil, struct

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


SAVEDIR = "Geneforge 2 Infestation Saved Games"
ROOT = None   # resolved lazily so --help works without the game installed

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
    "Essence": {"cur": (0xf6fe, 0x0f702), "max": 0xf700},
}
VITALS = {"Level": (0xf6ee, 2), "XP": (0x10014, 4)}
MAXV = 250   # refuse absurd values; the UI and combat math get weird past this


def path(slot):
    global ROOT
    if ROOT is None:
        ROOT = find_root()
    p = os.path.join(ROOT, "Save%d" % slot, "data")
    if not os.path.exists(p):
        sys.exit("no save at %s" % p)
    return p


def show(slot):
    d = open(path(slot), "rb").read()
    g = lambda o, w=2: struct.unpack_from("<h" if w == 2 else "<i", d, o)[0]
    print("== Save%d ==" % slot)
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


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    cmd, slot = sys.argv[1], int(sys.argv[2])
    if cmd == "show":
        show(slot)
    elif cmd == "set":
        setvals(slot, sys.argv[3:])
    elif cmd == "heal":
        heal(slot)
    elif cmd == "restore":
        restore(slot)
    else:
        sys.exit(__doc__)
