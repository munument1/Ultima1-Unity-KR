# -*- coding: utf-8 -*-
"""Audit new Ultima I Unity .NET user-string heap and v0.5 localized bytes.
Read only. Never changes game files. Requires _u1_v06_work/old_patch_data.json.
"""
from pathlib import Path
import json, base64, re, struct
HERE=Path(__file__).resolve().parent
WORK=HERE/'_u1_v06_work'
DLL=HERE/'Ultima I Unity'/'Ultima I Unity_Data'/'Managed'/'Ultima.Runtime.dll'
buf=DLL.read_bytes()
meta=buf.find(b'BSJB')
summary={'dll_bytes':len(buf),'metadata_file_offset':meta,'metadata_streams':{},'new_user_strings':[],
         'old_patch_korean_samples':[]}
def compressed(data,p):
    c=data[p]
    if c&0x80==0:return c,p+1
    if c&0xc0==0x80:return ((c&0x3f)<<8)|data[p+1],p+2
    if c&0xe0==0xc0:return ((c&0x1f)<<24)|(data[p+1]<<16)|(data[p+2]<<8)|data[p+3],p+4
    raise ValueError('reserved compressed integer')
if meta>=0:
    for stream in (b'#US\x00',b'#Strings\x00',b'#Blob\x00'):
        header=buf.find(stream,meta,meta+4096)
        if header<0:continue
        off,size=struct.unpack_from('<II',buf,header-8)
        start=meta+off
        summary['metadata_streams'][stream.decode('ascii','ignore').strip('\x00')]={'offset':start,'size':size,'valid':start+size<=len(buf)}
        if stream!=b'#US\x00' or start+size>len(buf):continue
        p=start+1; bad=0; entries=[]
        while p<start+size:
            rel=p-start
            try:
                ln,at=compressed(buf,p)
                end=at+ln
                if end>start+size:break
                content=buf[at:end]
                text=content[:-1].decode('utf-16le','replace') if ln>=1 else ''
                if text:
                    entries.append({'token':hex(0x70000000|rel),'text':text})
                p=end
            except Exception:bad+=1;break
        summary['user_string_total']=len(entries)
        summary['user_string_errors']=bad
        keywords=re.compile(r'custom|set builder|tile set|mixed|options|controller|tutorial|sprite|graphics|sound|reset',re.I)
        summary['new_user_strings']=[x for x in entries if keywords.search(x['text'])][:150]
        summary['user_string_hangul_count']=sum(bool(re.search('[가-힣]',x['text'])) for x in entries)
manifest=json.loads((WORK/'old_patch_data.json').read_text(encoding='utf-8'))
hangul=re.compile(r'[가-힣][가-힣A-Za-z0-9 \t.,:;!?()\/\-+\[\]\\]{1,100}')
total=0
for item in manifest['binary_files']:
    if not item['path'].endswith('Ultima.Runtime.dll'):continue
    for p in item['patches']:
        raw=base64.b64decode(p['data'])
        try:src=raw.decode('utf-16le','ignore')
        except Exception:continue
        vals=sorted(set(m.group(0).strip() for m in hangul.finditer(src)))
        if vals:
            total+=len(vals)
            if len(summary['old_patch_korean_samples'])<250:
                summary['old_patch_korean_samples'].append({'offset':p['offset'],'bytes':len(raw),'texts':vals[:12]})
summary['korean_segment_estimate']=total
(WORK/'dll_audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k not in ('new_user_strings','old_patch_korean_samples')},ensure_ascii=False,indent=2))
print('UI strings sample:',json.dumps(summary['new_user_strings'][:35],ensure_ascii=True))
print('Korean segment sample:',json.dumps(summary['old_patch_korean_samples'][:15],ensure_ascii=True))
