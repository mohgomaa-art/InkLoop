p = 'frontend/src/views/AgentStudioView.tsx'
with open(p, 'r', encoding='utf-8') as f:
    text = f.read()

target = '<div className="flex items-center gap-3 p-3.5 rounded-2xl bg-zinc-900/90 border border-white/10 text-xs text-zinc-300 animate-in fade-in max-w-md shadow-xl backdrop-blur-md">'
replacement = '<div className="flex items-center gap-3 py-2 px-1 text-xs text-zinc-300 animate-in fade-in">'

if target in text:
    text = text.replace(target, replacement)
    text = text.replace('size={32} message="InkLoop Agent Working"', 'size={38} message="InkLoop Agent Working"')
    text = text.replace('<span className="text-[11px] text-zinc-400 font-mono ml-auto">{activeActivityLabel}</span>', '{activeActivityLabel && <span className="text-[11px] text-zinc-400 font-mono">• {activeActivityLabel}</span>}')
    with open(p, 'w', encoding='utf-8') as f:
        f.write(text)
    print('Successfully removed box and modernized loading indicator!')
else:
    print('Target not found')
