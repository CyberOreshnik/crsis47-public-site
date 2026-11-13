"""Publish the owner's frozen homepage byte-for-byte; retain secondary pages."""
from pathlib import Path
import hashlib, json, shutil
source = Path('approved-website')
site = Path('site')
manifest = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
assert manifest['archive_sha256'] == '97e3647af487e045335a5e9aa8703786fb7a44ebdc162f5e504e814e78b14b4d'
assert len(manifest['files']) == 13
for name, digest in manifest['files'].items():
    assert Path(name).name == name
    data = (source / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest, (name, 'source checksum')
    shutil.copyfile(source / name, site / name)
    assert (site / name).read_bytes() == data
deployed = json.loads((site / 'deployment-manifest.json').read_text(encoding='utf-8'))
deployed['frozen_website'] = manifest
deployed['files'].update(manifest['files'])
(site / 'deployment-manifest.json').write_text(json.dumps(deployed, indent=2), encoding='utf-8')
print('PASS: 13 frozen files copied unchanged; secondary pages retained')
