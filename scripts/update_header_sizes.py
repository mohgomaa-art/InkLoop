import os

views = [
    'frontend/src/views/NarrativeTimelineView.tsx',
    'frontend/src/views/AssetLibraryView.tsx',
    'frontend/src/views/RunsHistoryView.tsx',
    'frontend/src/views/GenerationStudioView.tsx',
    'frontend/src/views/VerificationLabView.tsx',
    'frontend/src/views/CatalogueView.tsx',
    'frontend/src/views/BudgetsView.tsx',
    'frontend/src/views/BenchmarksView.tsx',
    'frontend/src/views/SettingsView.tsx'
]

for v in views:
    with open(v, 'r', encoding='utf-8') as f:
        c = f.read()
    if 'size={28}' in c:
        c = c.replace('size={28}', 'size={38}')
        with open(v, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"Updated {v} to size 38")
    else:
        print(f"size={28} not found in {v}")
