from __future__ import annotations
import csv, json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
AUDIT = ROOT / 'docs' / 'visual_forensics'

def jsonl(path: pathlib.Path) -> list[dict]:
    rows=[]
    with path.open(encoding='utf-8') as f:
        for n,line in enumerate(f,1):
            if not line.strip(): continue
            try: rows.append(json.loads(line))
            except Exception as exc: raise ValueError(f'{path}:{n}: {exc}')
    return rows

def main() -> int:
    files=jsonl(AUDIT/'inventory/files.jsonl')
    assets=jsonl(AUDIT/'inventory/registry_assets.jsonl')
    items=jsonl(AUDIT/'visual/items.jsonl')
    issues=jsonl(AUDIT/'issues/issues.jsonl')
    timeline=jsonl(AUDIT/'generation/timeline.jsonl')
    graph=json.loads((AUDIT/'lineage/graph.json').read_text(encoding='utf-8'))
    coverage=json.loads((AUDIT/'coverage.json').read_text(encoding='utf-8'))
    ledger=list(csv.DictReader((AUDIT/'inspection_ledger.csv').open(encoding='utf-8-sig',newline='')))
    def unique(rows,key,label):
        vals=[r.get(key) for r in rows]
        if None in vals or len(vals)!=len(set(vals)): raise ValueError(f'{label} has missing/duplicate {key}')
    for label,rows in [('files',files),('registry assets',assets),('visual items',items),('issues',issues)]:
        for r in rows:
            if r.get('audit_schema_version')!='1.0.0': raise ValueError(f'{label}: missing audit schema version')
    unique(files,'file_id','files'); unique(assets,'asset_id','registry assets'); unique(items,'visual_item_id','visual items'); unique(issues,'issue_id','issues')
    required={'scope','title','severity','status','confidence','affected_asset_ids','affected_paths','related_records','timestamps','prompts','lineage_and_references','expected_behavior','actual_observed_behavior','evidence','probable_root_cause','alternative_hypotheses','dependencies','next_investigation','recommended_correction','regression_tests','acceptance_criteria'}
    for i in issues:
        missing=required-set(i)
        if missing: raise ValueError(f"{i['issue_id']} missing {sorted(missing)}")
        for t in i['timestamps']:
            if not t.get('source'): raise ValueError(f"{i['issue_id']} timestamp has no source")
    issue_ids={i['issue_id'] for i in issues}
    bad_dependencies=[(i['issue_id'],dep) for i in issues for dep in i.get('dependencies',[]) if dep not in issue_ids]
    if bad_dependencies: raise ValueError(f'unknown issue dependencies: {bad_dependencies}')
    missing_time_sources=[r.get('event_id') for r in timeline if (r.get('timestamp') or r.get('generation_timestamp')) and not (r.get('timestamp_source') or r.get('generation_timestamp_explanation'))]
    if missing_time_sources: raise ValueError(f'{len(missing_time_sources)} timeline rows have timestamps without source labels')
    node_ids=[n['id'] for n in graph.get('nodes',[])]
    if len(node_ids)!=len(set(node_ids)): raise ValueError('duplicate graph node IDs')
    node_set=set(node_ids)
    dangling=[e for e in graph.get('edges',[]) if e.get('from') not in node_set or e.get('to') not in node_set]
    if dangling: raise ValueError(f'{len(dangling)} dangling graph endpoints')
    if any(not e.get('verification') for e in graph.get('edges',[])): raise ValueError('graph edge lacks verification state')
    item_ids={i['visual_item_id'] for i in items}
    bad_assets=[a['asset_id'] for a in assets if a.get('visual_item_id') not in item_ids]
    if bad_assets: raise ValueError(f'{len(bad_assets)} registry images lack a visual item')
    file_ids={f['file_id'] for f in files}
    missing_item_paths=[sid for i in items for sid in i.get('source_file_ids',[]) if sid.startswith('file:') and sid not in file_ids]
    if missing_item_paths: raise ValueError(f'{len(missing_item_paths)} visual item file links unresolved')
    if coverage.get('full_visual_coverage') is not False: raise ValueError('coverage incorrectly claims full visual review')
    if coverage.get('workspace_snapshot_stable') is not False or coverage.get('database_files_stable') is not False: raise ValueError('unstable source snapshot not flagged')
    if len(issues)!=9: raise ValueError(f'expected 9 issue records, got {len(issues)}')
    report={'result':'PASS','issues':len(issues),'files_and_git_blobs':len(files),'registry_images':len(assets),'visual_items':len(items),'timeline_rows':len(timeline),'graph_nodes':len(node_ids),'graph_edges':len(graph.get('edges',[])),'graph_dangling_edges':0,'unresolved_asset_reference_edges':sum(e.get('verification')=='unresolved_asset_id' for e in graph.get('edges',[])),'ledger_rows':len(ledger),'full_visual_coverage':coverage['full_visual_coverage'],'workspace_snapshot_stable':coverage['workspace_snapshot_stable'],'database_files_stable':coverage['database_files_stable']}
    print(json.dumps(report,indent=2));return 0
if __name__=='__main__':
    try: sys.exit(main())
    except Exception as e:
        print(f'VALIDATION FAILED: {e}',file=sys.stderr);sys.exit(1)
