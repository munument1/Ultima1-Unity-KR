# -*- coding: utf-8 -*-
"""Ultima I Unity 2026-10-11 -> Korean v0.6 migration PRE-FLIGHT.
Reads the already-extracted game ONLY. Never changes game binaries/JSON.
Retrieves prior Korean delta-package as a SOURCE OF TRANSLATIONS, not as a new game build.
"""
from pathlib import Path
import base64
import hashlib
import json
import os
import re
import urllib.request
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE / "Ultima I Unity"
DATA = ROOT / "Ultima I Unity_Data"
WORK = HERE / "_u1_v06_work"
WORK.mkdir(exist_ok=True)
SOURCE_URL = "https://github.com/munument1/-KR-ULTIMA1-UNITY/releases/download/v0.5/Ultima1Unity_Korean_v0.5_DeltaPatch.zip"
OLD_ZIP = WORK / "Ultima1Unity_Korean_v0.5_DeltaPatch.zip"
EXPECTED_OLD_ZIP_HASH = "358a9f7c99ba8214b2f60dc8e74f81578afb65517550e9689e4cfa03c556f2c1"
PATHS = ("Managed/Ultima.Runtime.dll", "resources.assets",
         "StreamingAssets/location_data.json", "StreamingAssets/shop_data.json")

def digest(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def path_by_manifest(path):
    path = path.replace("\\", "/")
    prefix = "Ultima I Unity_Data/"
    assert path.startswith(prefix), "Unexpected manifest path: " + path
    return DATA / path[len(prefix):]

def path_exists(target, pieces):
    node = target
    for part in pieces:
        val = part.get("value")
        if part.get("kind") == "index":
            if not isinstance(node, list) or not (0 <= int(val) < len(node)):
                return False
            node = node[int(val)]
        else:
            if not isinstance(node, dict) or str(val) not in node:
                return False
            node = node[str(val)]
    return True

report = {"game_directory": str(ROOT), "files": {}, "old_patch": {},
          "json_migration": [], "warnings": []}
for relative in PATHS:
    p = DATA / relative
    report["files"][relative] = {"exists": p.is_file()}
    if p.is_file():
        report["files"][relative].update(bytes=p.stat().st_size, sha256=digest(p))

if not OLD_ZIP.is_file():
    try:
        req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Ultima-I-Unity-Korean-maintainer"})
        with urllib.request.urlopen(req, timeout=30) as r, OLD_ZIP.open("wb") as f:
            while True:
                buf = r.read(1024 * 1024)
                if not buf:
                    break
                f.write(buf)
    except Exception as ex:
        report["warnings"].append("v0.5 translation source download failed: " + repr(ex))

if OLD_ZIP.is_file():
    old_hash = digest(OLD_ZIP)
    report["old_patch"]["zip_sha256"] = old_hash
    report["old_patch"]["verified"] = old_hash == EXPECTED_OLD_ZIP_HASH
    if old_hash != EXPECTED_OLD_ZIP_HASH:
        report["warnings"].append("Old patch SHA mismatch; no migration generated")
    else:
        with zipfile.ZipFile(OLD_ZIP) as archive:
            names = archive.namelist()
            report["old_patch"]["entries"] = names
            manifest = json.loads(archive.read("patch_data.json").decode("utf-8-sig"))
        report["old_patch"]["version"] = manifest.get("version")
        report["old_patch"]["dll_patches"] = [
            {"path": f["path"], "original_hash": f["original_sha256"],
             "patched_hash": f["patched_sha256"], "blocks": len(f["patches"]),
             "bytes": sum(len(base64.b64decode(p["data"])) for p in f["patches"])}
            for f in manifest.get("binary_files", [])
        ]
        for f in manifest.get("json_files", []):
            p = path_by_manifest(f["path"])
            entry = {"path": f["path"], "found": p.is_file(),
                     "source_updates": len(f.get("updates", []))}
            if p.is_file():
                new_json = json.loads(p.read_text(encoding="utf-8-sig"))
                existing = [u for u in f.get("updates", []) if path_exists(new_json, u["path"])]
                missing = [u for u in f.get("updates", []) if not path_exists(new_json, u["path"])]
                entry.update(valid_path_updates=len(existing), missing_path_updates=len(missing),
                             missing_samples=missing[:12], new_original_sha256=digest(p),
                             same_as_old=f["original_sha256"].lower()==digest(p))
            report["json_migration"].append(entry)
        (WORK / "old_patch_data.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
( WORK / "probe_report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2)[:26000])
