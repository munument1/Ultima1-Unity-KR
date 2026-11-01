"""Create a detached current-build resource candidate with a full Korean font.

Only PrintChar21.m_FontData may change. Every other Unity object's raw payload
and every other field of the target Font are checked after serialization.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path

import UnityPy
from fontTools.ttLib import TTFont

SOURCE_SHA = 'f47660f028688a1a3f58ebf4b6f65d50acf258b3b909e869227cf30d2cd7283f'
FONT_SHA = 'e24256f42e43713d2ea086a1e1669d78b968f5b3cc547e5c157f0606ffa5def1'
OLD_FONT_SHA = 'c199b39eeae2a817c4f44bd1bdbcbead974e87dc4c7401193db831be2f2470e1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def build(source, font, output):
    source, font, output = map(Path, (source, font, output))
    if output.resolve() in (source.resolve(), font.resolve()) or output.exists():
        raise ValueError('Output must be a new detached file')
    if UnityPy.__version__ != '1.25.2':
        raise ValueError('Use the verified UnityPy 1.25.2 serializer')
    raw, font_bytes = source.read_bytes(), font.read_bytes()
    if sha(raw) != SOURCE_SHA or sha(font_bytes) != FONT_SHA:
        raise ValueError('Unreviewed source resource or font SHA-256')
    cmap = TTFont(io.BytesIO(font_bytes)).getBestCmap()
    if sum(0xAC00 <= cp <= 0xD7A3 for cp in cmap) != 11172:
        raise ValueError('Font lacks complete modern Hangul coverage')
    env = UnityPy.load(raw)
    objects = {o.path_id: o for o in env.objects}
    before = {key: sha(obj.get_raw_data()) for key, obj in objects.items()}
    matches = [o for o in objects.values() if o.type.name == 'Font'
               and o.read_typetree().get('m_Name') == 'PrintChar21']
    if len(matches) != 1:
        raise ValueError('Expected exactly one PrintChar21 Font')
    target = matches[0]
    tree = target.read_typetree()
    if sha(bytes(tree['m_FontData'])) != OLD_FONT_SHA:
        raise ValueError('Unreviewed existing font content')
    target_id = target.path_id
    tree['m_FontData'] = list(font_bytes)
    target.save_typetree(tree)
    result = env.file.save()
    checked = {o.path_id: o for o in UnityPy.load(result).objects}
    if checked.keys() != objects.keys():
        raise ValueError('Resource object identities changed')
    changed = [key for key, obj in checked.items() if sha(obj.get_raw_data()) != before[key]]
    if changed != [target_id]:
        raise ValueError(f'Unexpected changed objects: {changed}')
    after_tree = checked[target_id].read_typetree()
    if after_tree != tree:
        raise ValueError('Font field readback mismatch')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result)
    if sha(output.read_bytes()) != sha(result):
        raise ValueError('Output readback hash mismatch')
    return dict(source_sha256=sha(raw), output_sha256=sha(result),
                font_sha256=sha(font_bytes), font_path_id=target_id,
                objects=len(objects), changed_objects=changed,
                unchanged_object_payloads_verified=True,
                only_m_FontData_changed=True, modern_hangul_glyphs=11172,
                game_verified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('source', 'font', 'output', 'report'):
        parser.add_argument('--' + flag, type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists() or args.report.resolve() in {
            args.source.resolve(), args.font.resolve(), args.output.resolve()}:
        parser.error('Report must be a new file separate from source, font and output')
    report = build(args.source, args.font, args.output)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))
