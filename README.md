# gfedit — Geneforge 2: Infestation save editor

A small, dependency-free Python script for editing character stats in
**Geneforge 2: Infestation** (Spiderweb Software) save files.

## Save format

Saves live in `Documents/Spiderweb Software/Geneforge 2 Infestation Saved Games/SaveN/`
and are **uncompressed, unencrypted, fixed-size struct dumps** — no checksum.
Each slot holds four files; all character data is in `data`.

| file     | size       | contents                                  |
|----------|------------|-------------------------------------------|
| `header` | 364,928    | slot label, zone name, terrain            |
| `data`   | 13,244,456 | character, creatures, objects, flags      |
| `items`  | 3,600,000  | coordinate tables                         |
| `journal`| varies     | quest log                                 |

**Slot directories are zero-indexed**: in-game "slot 2" is `Save1/`.
`Save18` / `Save19` are the quicksave and autosave.

## Usage

```
python gfedit.py show 1                     # dump current values
python gfedit.py heal 1                     # fill all pools to max
python gfedit.py set 1 Stealth=8 Melee=10   # patch by name
python gfedit.py restore 1                  # undo the last write
```

The trailing number is the **directory** number, not the in-game slot label.

Set `GF2_SAVES` to point at a non-default save folder:

```
GF2_SAVES="/path/to/Geneforge 2 Infestation Saved Games" python gfedit.py show 1
```

## Editable fields

**Pools** (`HealthCur`/`HealthMax`, `EnergyCur`/`EnergyMax`, `EssenceCur`/`EssenceMax`)
are stored as three int16 slots each — `[current, max, current_mirror]`. The script
writes both current-slots together; writing only one desyncs them.

**Skills** are int16 at `0xf77c`–`0xf7aa`, laid out as 5 attributes, then repeating
groups of 4 skills separated by 1 unused slot. All 20 are addressable by name.

Skill values are **invested points only**. The character sheet adds species, level and
equipment bonuses on top, so a skill storing 4 may display as 6. Editing here raises
the invested half; the bonus sources live elsewhere in the file.

## Caveats

- **Quit the game before editing.** A running session can flush its own state over your
  changes when it saves.
- Edits are strictly in-place; the file length is fixed and the script refuses to write
  if it ever changes.
- The save folder is **Steam Cloud synced**. An edit that appears to revert itself was
  probably overwritten by a cloud restore.
- Every write makes a `.bak` first, but each new write overwrites that backup. Keep your
  own copy of a save you care about.

## How the offsets were found

Diff two saves where exactly one known value changed, filter for byte deltas of `+1`,
then rank candidates by how *quiet* the surrounding bytes are — the real stat block had
zero other changes within ±96 bytes, while noise regions had dozens. Then write a probe
pattern (distinct multiples of 10) across the array and read one character-sheet
screenshot to map every slot at once.

Offsets confirmed against one save at version 1.0. Treat them as version-specific.
