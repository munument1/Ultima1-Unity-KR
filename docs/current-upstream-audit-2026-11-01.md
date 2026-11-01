# Current upstream verification — 2026-11-01

Refs #3 and #4. This is a read-only maintenance audit, not a v0.6 release.

The official itch.io page still offers upload **19704696**. A fresh anonymous
download of that exact upload produced a valid ZIP (CRC check passed):

- ZIP size: **434,933,321 bytes**.
- ZIP SHA-256: `9edf26c1f692a93ecf7a6fa51c083ef2261193f15eec26a7b3f0368090375bc4`.

Its four relevant files match the 2026-10-15 migration audit exactly:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| Managed/Ultima.Runtime.dll | 1,735,168 | `7a2125c2fabcf96ab4f6babd17fb76b3cdd688b94c0e88602ef5933c8aa2efe3` |
| resources.assets | 13,253,964 | `f47660f028688a1a3f58ebf4b6f65d50acf258b3b909e869227cf30d2cd7283f` |
| StreamingAssets/location_data.json | 8,888 | `c21ddac21748be22501f0ecfe4721e6a805a0b85cb46d05cd344120f2e7951b6` |
| StreamingAssets/shop_data.json | 46,548 | `b7929090d8242c759e9251286c34e5a65ea53b95adf2bb7e17be5c6d7d9b6700` |

The v0.5 translation package was also rehashed and still matches
`358a9f7c99ba8214b2f60dc8e74f81578afb65517550e9689e4cfa03c556f2c1`.
Both JSON originals match that package's expected originals. All **83 location**
and **1,042 shop** update paths resolve to strings, so the **1,125 JSON updates**
can carry forward without path remapping.

## Remaining implementation

1. Recover a trustworthy English-to-Korean DLL string mapping or the exact
   2026-09-13 original DLL and its localization tooling. The repository holds
   504 binary replacement blocks, not a complete reusable translation map.
   Applying their offsets to the current DLL is unsafe. The old public itch
   download request for upload 19228780 did not return a download URL during
   this audit; that does not prove no other copy exists.
2. Reinsert Galmuri11 into the current Unity resource structure and retarget
   the current DLL's font references. The old resources delta is not portable
   across the changed file layout.
3. Review new UI/Set Builder strings, then create a new hash-pinned delta and
   verify rendering, save/load, installation and restoration in a test copy.

Issue #3 describes an older upload; current implementation should target #4's
19704696 rather than produce two separate intermediate releases. Neither the
supported v0.5 baseline nor `upstream_state.json` was advanced: a fresh upstream
fingerprint alone does not establish Korean patch compatibility. No live game
files, public releases or issue states were changed.

Official source: <https://archiveofmyth.itch.io/ultima-unity>.
