import json

with open('coverage.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print('=== testmanager_app 各功能文件覆盖率 ===')
print()

files = []
for f, info in data['files'].items():
    if 'testmanager_app' in f:
        summary = info['summary']
        total = summary['num_statements']
        pct = summary['percent_covered']
        if total > 0:
            files.append((f, pct, total, summary['covered_lines']))

files.sort(key=lambda x: x[1])

print('File                                                        %   Total Covered')
print('-' * 80)
for f, pct, total, covered in files:
    print(f'{f:<60} {int(pct):>5}% {total:>6} {covered:>6}')