"""Publish the reviewed checksum-frozen website without transforming its bytes."""
from pathlib import Path
import hashlib,json
source=Path('approved-website');site=Path('site')
manifest=json.loads((source/'manifest.json').read_text(encoding='utf-8'))
assert manifest['archive_sha256']=='4549963da97362c1efa4875407fb7622ac2a1e4052ebf4297e9c8e7baf8bbfb4'
assert len(manifest['files'])==28
for name,digest in manifest['files'].items():
 path=Path(name)
 assert not path.is_absolute() and '..' not in path.parts
 data=(source/path).read_bytes()
 assert hashlib.sha256(data).hexdigest()==digest,(name,'source checksum')
 target=site/path;target.parent.mkdir(parents=True,exist_ok=True)
 target.write_bytes(data)
 assert target.read_bytes()==data
deployed=json.loads((site/'deployment-manifest.json').read_text(encoding='utf-8'))
deployed['frozen_website']=manifest;deployed['files'].update(manifest['files'])
(site/'deployment-manifest.json').write_text(json.dumps(deployed,indent=2),encoding='utf-8')
print('PASS:',len(manifest['files']),'frozen files copied unchanged; legacy book pages retained')
