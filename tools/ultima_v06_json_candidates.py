# -*- coding: utf-8 -*-
"""Prepare v0.6 JSON translation candidates from the v0.5 patch's translation data.
DOES NOT MODIFY ORIGINAL GAME FILES. Requires _u1_v06_work/old_patch_data.json.
"""
from pathlib import Path
import hashlib, json, copy
HERE=Path(__file__).resolve().parent
GAME=HERE/'Ultima I Unity'/'Ultima I Unity_Data'
WORK=HERE/'_u1_v06_work'
SRC=WORK/'old_patch_data.json'
DEST=WORK/'candidate_json'
DEST.mkdir(parents=True,exist_ok=True)
def digest(data):
    return hashlib.sha256(data).hexdigest()
def getpath(mpath):
    s=mpath.replace('\\','/')
    pre='Ultima I Unity_Data/'
    if not s.startswith(pre):raise ValueError(s)
    return s[len(pre):]
def getroot(root,path):
    cursor=root
    for p in path:
        if p['kind']=='index': cursor=cursor[int(p['value'])]
        else: cursor=cursor[str(p['value'])]
    return cursor
def assign(root,path,val):
    cursor=root
    for p in path[:-1]:
        if p['kind']=='index':cursor=cursor[int(p['value'])]
        else:cursor=cursor[str(p['value'])]
    last=path[-1]
    if last['kind']=='index':cursor[int(last['value'])]=val
    else:cursor[str(last['value'])]=val
manifest=json.loads(SRC.read_text(encoding='utf-8'))
report={'source_version':manifest.get('version'),'candidates':[],'WARNING':'Candidates are NOT reviewed and cannot be published without semantic checks.'}
for f in manifest.get('json_files',[]):
    rel=getpath(f['path'])
    in_path=GAME/rel
    if not in_path.is_file():
        report['candidates'].append({'path':rel,'status':'missing'})
        continue
    raw=in_path.read_bytes()
    root=json.loads(raw.decode('utf-8-sig'))
    patched=copy.deepcopy(root)
    safe=[]
    unresolved=[]
    unchanged=0
    for u in f['updates']:
        try:
            before=getroot(patched,u['path'])
            if type(before)!=type(u['value']):raise TypeError(f'value type changed from {type(before).__name__}')
            if before==u['value']:
                unchanged+=1
                continue
            assign(patched,u['path'],u['value'])
            safe.append({'path':u['path'],'value':u['value'],'was':before})
        except (KeyError,IndexError,TypeError,ValueError) as exc:
            unresolved.append({'path':u['path'],'value':u['value'],'reason':str(exc)})
    payload=(json.dumps(patched,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    outfile=DEST/rel.replace('/','__')
    outfile.parent.mkdir(exist_ok=True)
    outfile.write_bytes(payload)
    report['candidates'].append({
        'path':rel,'source_original_sha256':digest(raw),'candidate_sha256':digest(payload),
        'source_updates':len(f['updates']),'carried_forward':len(safe),
        'unchanged':unchanged,'unresolved':len(unresolved),
        'unresolved_details':unresolved[:100],'changed_samples':safe[:20],
        'candidate_file':str(outfile),
        'WARNING':'Source index positions are assumed to match; verify names/entities before release'
    })
(WORK/'json_candidates_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2)[:24000])
