"""Validate PBIR JSON against Microsoft schemas and semantic-model references."""
from pathlib import Path
import json
import urllib.request
from urllib.parse import urldefrag
from jsonschema import Draft7Validator
from referencing import Registry,Resource
from referencing.jsonschema import DRAFT7
from revpulse.core import json_write

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'.local/schema-cache';CACHE.mkdir(exist_ok=True)

def retrieve(uri):
    import hashlib
    uri=urldefrag(uri)[0]
    filename=CACHE/(hashlib.sha256(uri.encode()).hexdigest()+'.json')
    if not filename.exists():filename.write_bytes(urllib.request.urlopen(uri,timeout=30).read())
    return Resource.from_contents(json.loads(filename.read_text()),default_specification=DRAFT7)

def main():
    registry=Registry(retrieve=retrieve);checked=[]
    for file in (ROOT/'dashboard/RevPulse.Report/definition').rglob('*.json'):
        obj=json.loads(file.read_text());uri=obj['$schema']
        resource=retrieve(uri);reg=registry.with_resource(uri,resource)
        validator=Draft7Validator(resource.contents,registry=reg)
        # Resolve relative references from the root schema's canonical URL.
        validator=Draft7Validator({'$ref':uri},registry=reg)
        errors=list(validator.iter_errors(obj))
        if errors:raise ValueError(str(file)+': '+ '; '.join(e.message for e in errors))
        checked.append(str(file.relative_to(ROOT)))
    model=json.loads((ROOT/'dashboard/RevPulse.SemanticModel/model.bim').read_text())['model']
    tables={t['name']:{c['name'] for c in t['columns']} for t in model['tables']}
    measures={t['name']:{m['name'] for m in t.get('measures',[])} for t in model['tables']}
    for rel in model['relationships']:
        if rel['fromColumn'] not in tables[rel['fromTable']] or rel['toColumn'] not in tables[rel['toTable']]:raise ValueError('Invalid relationship')
    for file in (ROOT/'dashboard/RevPulse.Report').rglob('visual.json'):
        obj=json.loads(file.read_text())
        for state in obj['visual']['query']['queryState'].values():
            for projection in state['projections']:
                field=projection['field'];kind=next(iter(field));v=field[kind];entity=v['Expression']['SourceRef']['Entity']
                if v['Property'] not in (measures if kind=='Measure' else tables)[entity]:raise ValueError(f'Invalid field in {file}')
    json_write(ROOT/'reports/powerbi_schema_validation.json',{'status':'passed','checked_files':checked,'tables':len(tables),'relationships':len(model['relationships']),'native_refresh':'Deferred by user; schema validation does not verify DAX evaluation or visual rendering.'})
    print(f'Validated {len(checked)} PBIR definitions and all model references')

if __name__=='__main__':main()
