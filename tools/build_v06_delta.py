"""Build copy/data deltas; unchanged original game bytes are referenced, not bundled."""
import hashlib,json,zipfile,shutil,argparse
from pathlib import Path
def sha(b): return hashlib.sha256(b).hexdigest()
EXPECTED={
'Managed/Ultima.Runtime.dll':('7a2125c2fabcf96ab4f6babd17fb76b3cdd688b94c0e88602ef5933c8aa2efe3','f5356389f951de70cfb49080b5be404ec2b3b54fab323687fa921f2926c184e2'),
'resources.assets':('f47660f028688a1a3f58ebf4b6f65d50acf258b3b909e869227cf30d2cd7283f','683a16ba575b2f34c67ac792d8cc890665c72034dc83f3d38061cf81d33256ae'),
'StreamingAssets/location_data.json':('c21ddac21748be22501f0ecfe4721e6a805a0b85cb46d05cd344120f2e7951b6',None),
'StreamingAssets/shop_data.json':('b7929090d8242c759e9251286c34e5a65ea53b95adf2bb7e17be5c6d7d9b6700',None)}
def delta(old,new,blob):
    index={}
    for i in range(0,len(old)-63,16): index.setdefault(old[i:i+64],i)
    ops=[]; i=0; start=0
    while i<len(new):
        j=index.get(new[i:i+64]) if i+64<=len(new) else None
        if j is None: i+=1; continue
        if i>start: ops.append(['data',len(blob),i-start]); blob.extend(new[start:i])
        n=64
        while j+n+4096<=len(old) and i+n+4096<=len(new) and old[j+n:j+n+4096]==new[i+n:i+n+4096]: n+=4096
        while j+n<len(old) and i+n<len(new) and old[j+n]==new[i+n]: n+=1
        ops.append(['copy',j,n]); i+=n; start=i
    if i>start: ops.append(['data',len(blob),i-start]); blob.extend(new[start:i])
    rebuilt=b''.join(old[o:o+n] if k=='copy' else blob[o:o+n] for k,o,n in ops)
    assert rebuilt==new
    return ops
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--original',type=Path,required=True); ap.add_argument('--patched',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=False); blob=bytearray(); files=[]
    for name,(before,after) in EXPECTED.items():
        old=(a.original/name).read_bytes(); new=(a.patched/name).read_bytes()
        assert sha(old)==before,name
        if after: assert sha(new)==after,name
        else: assert isinstance(json.loads(new),type(json.loads(old)))
        files.append(dict(path='Ultima I Unity_Data/'+name,original_sha256=sha(old),patched_sha256=sha(new),original_size=len(old),patched_size=len(new),operations=delta(old,new,blob)))
    manifest=dict(version='0.6',upstream_upload=19704696,game_verified=False,translation_review_complete=False,payload_sha256=sha(blob),files=files)
    (a.output/'patch.bin').write_bytes(blob); (a.output/'patch.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    shutil.copy2(Path(__file__).with_name('Install-v06.ps1'),a.output/'Install_Korean_Patch.ps1')
    for action,switch in [('Install',''),('Restore',' -Restore')]:
        (a.output/f'{action}_Korean_Patch.bat').write_bytes(('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install_Korean_Patch.ps1"'+switch+'\r\nif errorlevel 1 echo Patch failed. Read the error above.\r\npause\r\n').encode('ascii'))
    shutil.copy2(Path(__file__).parents[1]/'docs/releases/v0.6.md',a.output/'README_KO.md')
    print(json.dumps({'payload_bytes':len(blob),'files':[{k:v for k,v in f.items() if k!='operations'} for f in files]},indent=2))
if __name__=='__main__': main()
