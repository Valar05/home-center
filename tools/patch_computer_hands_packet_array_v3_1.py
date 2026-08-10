from pathlib import Path

path = Path('computer-hands/windows/home-center-hands.ps1')
text = path.read_text(encoding='utf-8')

replacements = [
    ('$results=New-Object System.Collections.Generic.List[object]', '$results=@()'),
    ('$results.Add([pscustomobject]@{id=$stepId;action=$stepAction;ok=($stepResult.ok -ne $false);result=$stepResult})', '$results += [pscustomobject]@{id=$stepId;action=$stepAction;ok=($stepResult.ok -ne $false);result=$stepResult}'),
    ('$results.Add([pscustomobject]@{id=$stepId;action=$stepAction;ok=$false;error=$_.Exception.Message})', '$results += [pscustomobject]@{id=$stepId;action=$stepAction;ok=$false;error=$_.Exception.Message}'),
    ('steps=@($results)', 'steps=$results'),
]

for old, new in replacements:
    count = text.count(old)
    if old == 'steps=@($results)':
        if count != 2:
            raise SystemExit(f'expected 2 packet result-array matches, found {count}')
        text = text.replace(old, new)
    else:
        if count != 1:
            raise SystemExit(f'expected 1 match for {old!r}, found {count}')
        text = text.replace(old, new, 1)

path.write_text(text, encoding='utf-8')
print('Computer Hands packet array v3.1 patch applied')
