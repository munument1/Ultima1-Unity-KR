# Detached v0.6 migration candidates

Requires .NET 9 and Mono.Cecil 0.11.6 (pinned in the project). This tool reads a
hash-pinned released v0.3 Korean DLL and the current official DLL. It never
patches either input. No original game binaries are included in the repository.

```powershell
dotnet run --project tools/UltimaMigration -- DONOR.dll CURRENT.dll REPORT.json CANDIDATE.dll
```

Omit `CANDIDATE.dll` to extract candidates only. Report and candidate paths must
be new and separate from the input assemblies. Create the destination directory
first. Repeated builds are deterministic.

- Compare full method identities, opcodes, non-string operands, local types,
  branch targets and exception handlers before recovering each string site.
- Apply translations only at those exact unchanged-method sites. A matching
  English word elsewhere is never sufficient authorization to replace it.
- Quarantine source sites involving resource paths, persistence/import,
  inventory lookup, rendering/class normalization and Data constructors.
  The prior donor contains Korean replacements in some such contexts; previous
  release provenance does not make these safe for the new version.
- Redirect the reviewed Font resource paths to PrintChar21. Ten direct baked
  TMP loads use the game's existing `UIFonts.FromTtf(string)` loader instead,
  preserving the one-string/static/TMP-result call contract. The corresponding
  resource candidate contains a complete modern Hangul font.
- Reopen the candidate DLL and verify every method's instructions, operands,
  locals and exception handlers; permit only the logged string operands and
  reviewed font call targets to differ.

## Font resource candidate

Install `tools/requirements-migration.txt`, then run:

```powershell
python tools/ultima_v06_font.py --source CURRENT.resources.assets --font Galmuri11.ttf --output CANDIDATE.resources.assets --report FONT-REPORT.json
```

The current resource and the complete Galmuri11 input are SHA-pinned in the
script. Only the PrintChar21 object's `m_FontData` field may change. After writing,
all other 6,725 object payloads and all other Font fields must match. Galmuri's
OFL license is retained in the repository's `LICENSE_Galmuri.txt`.

These are **incomplete development candidates**, not a v0.6 installer or release.
Unmatched and quarantined strings require contextual review, and graphical
rendering, all game systems, save/load and restore remain release gates.
