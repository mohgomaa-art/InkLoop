import os
import re

views_to_update = [
    {
        'path': 'frontend/src/views/NarrativeTimelineView.tsx',
        'tab': 'timeline',
        'target': '<Clock className="w-5 h-5 text-white" />',
        'replacement': '<TabCharacterIcon tab="timeline" size={28} />'
    },
    {
        'path': 'frontend/src/views/AssetLibraryView.tsx',
        'tab': 'assets',
        'target': '<Database className="w-5 h-5 text-white" />',
        'replacement': '<TabCharacterIcon tab="assets" size={28} />'
    },
    {
        'path': 'frontend/src/views/RunsHistoryView.tsx',
        'tab': 'batches',
        'target': '<Layers className="w-5 h-5 text-white" />',
        'replacement': '<TabCharacterIcon tab="batches" size={28} />'
    },
    {
        'path': 'frontend/src/views/GenerationStudioView.tsx',
        'tab': 'studio',
        'target': '<Sparkles className="w-5 h-5 text-white" />',
        'replacement': '<TabCharacterIcon tab="studio" size={28} />'
    },
    {
        'path': 'frontend/src/views/VerificationLabView.tsx',
        'tab': 'verification',
        'target': '<ShieldCheck className="w-5 h-5 text-emerald-400" />',
        'replacement': '<TabCharacterIcon tab="verification" size={28} />'
    },
    {
        'path': 'frontend/src/views/CatalogueView.tsx',
        'tab': 'catalogue',
        'target': '<Library className="w-5 h-5 text-white" />',
        'replacement': '<TabCharacterIcon tab="catalogue" size={28} />'
    },
    {
        'path': 'frontend/src/views/BudgetsView.tsx',
        'tab': 'budgets',
        'target': '<Coins className="w-5 h-5 text-amber-400" />',
        'replacement': '<TabCharacterIcon tab="budgets" size={28} />'
    },
    {
        'path': 'frontend/src/views/BenchmarksView.tsx',
        'tab': 'benchmarks',
        'target': '<BarChart3 className="w-5 h-5 text-white" />',
        'replacement': '<TabCharacterIcon tab="benchmarks" size={28} />'
    },
    {
        'path': 'frontend/src/views/SettingsView.tsx',
        'tab': 'settings',
        'target': '<Settings className="w-5 h-5 text-white" />',
        'replacement': '<TabCharacterIcon tab="settings" size={28} />'
    },
    {
        'path': 'frontend/src/views/WorkspaceView.tsx',
        'tab': 'workspace',
        'target': '<span className="welcome-mark"><Sparkles /></span>',
        'replacement': '<TabCharacterIcon tab="workspace" size={32} />'
    }
]

for item in views_to_update:
    path = item['path']
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Ensure TabCharacterIcon is imported
    if 'TabCharacterIcon' not in content:
        if 'import { apiClient }' in content:
            content = content.replace(
                'import { apiClient }',
                "import { TabCharacterIcon } from '../components/agent/character';\nimport { apiClient }"
            )
        else:
            # Add at top after first import
            first_import_end = content.find(';\n')
            if first_import_end != -1:
                content = (
                    content[:first_import_end + 2] +
                    "import { TabCharacterIcon } from '../components/agent/character';\n" +
                    content[first_import_end + 2:]
                )

    if item['target'] in content:
        content = content.replace(item['target'], item['replacement'])
        print(f"Successfully replaced in {path} for tab {item['tab']}")
    else:
        print(f"Target not found in {path}: {item['target']}")

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

# Now also check AgentStudioView.tsx
with open('frontend/src/views/AgentStudioView.tsx', 'r', encoding='utf-8') as f:
    studio_content = f.read()

if 'TabCharacterIcon' not in studio_content:
    studio_content = studio_content.replace(
        "import { AgentCharacter } from '../components/agent/character';",
        "import { AgentCharacter, TabCharacterIcon } from '../components/agent/character';"
    )

# Replace the bot squircle icon in sessions sidebar
old_bot = '''                <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-neutral-500 to-neutral-100 flex items-center justify-center shadow-[0_0_12px_rgba(255,255,255,0.10)]">
                  <Bot className="w-4 h-4 text-white" />
                </div>'''
new_bot = '''                <TabCharacterIcon tab="agent" size={28} />'''

if old_bot in studio_content:
    studio_content = studio_content.replace(old_bot, new_bot)
    print("Replaced Bot icon in AgentStudioView sidebar")
else:
    print("Warning: old_bot not found in AgentStudioView.tsx")

with open('frontend/src/views/AgentStudioView.tsx', 'w', encoding='utf-8') as f:
    f.write(studio_content)

print("All view headers updated!")

# Update AgentStudioView pill
with open('frontend/src/views/AgentStudioView.tsx', 'r', encoding='utf-8') as f:
    text = f.read()

target = '<div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/[0.03] border border-white/10 text-xs text-ink-300">'
repl = '<div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-white/[0.03] border border-white/10 text-xs text-ink-300">\n              <TabCharacterIcon tab="agent" size={16} />'

if target in text and 'size={16}' not in text:
    text = text.replace(target, repl, 1)
    with open('frontend/src/views/AgentStudioView.tsx', 'w', encoding='utf-8') as f:
        f.write(text)
    print('Updated AgentStudioView header pill!')
