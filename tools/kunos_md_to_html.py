"""Convert docs/04_kunos_licenses_proposal.md into docs/Kunos_Licenses.html
using the same table layout as docs/GT_Licenses.html."""
import re, html

e = html.escape
L = open('docs/04_kunos_licenses_proposal.md', encoding='utf-8').read().splitlines()


def md(s):
    s = e(s)
    s = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', s)
    s = re.sub(r'\*(.+?)\*', r'<em>\1</em>', s)
    s = re.sub(r'`(.+?)`', r'<code>\1</code>', s)
    return s


def tex(s):
    def fix(m):
        return (re.sub(r'\\text\{(.*?)\}', r'\1', m.group(1))
                .replace('\\circ', '°').replace('\\rightarrow', '→'))
    return re.sub(r'\$(.+?)\$', fix, s)


out = ['<h1>Gran Turismo-Style License Tests Proposal (Kunos Official Resources)</h1>']
i2 = next(i for i, l in enumerate(L) if l.startswith('## 2.'))
lst = None
for l in L[2:i2]:
    l = tex(l)
    if l.startswith('## ') or l.startswith('### '):
        if lst:
            out.append('</%s>' % lst); lst = None
        n = l.split(' ')[0]
        out.append('<h%d>%s</h%d>' % (len(n), e(l[len(n) + 1:]), len(n)))
    elif re.match(r'(\* |\d+\. )', l):
        t = 'ul' if l[0] == '*' else 'ol'
        if lst != t:
            if lst:
                out.append('</%s>' % lst)
            out.append('<%s>' % t); lst = t
        out.append('<li>%s</li>' % md(re.sub(r'^(\* |\d+\. )', '', l)))
    elif l.strip() and l.strip() != '---':
        if lst:
            out.append('</%s>' % lst); lst = None
        out.append('<p>%s</p>' % md(l))
if lst:
    out.append('</%s>' % lst)

tiers = []; cur = None; t = None
for l in L[i2:]:
    if re.match(r'## [2-6]\.', l):
        cur = {'name': re.sub(r'^## \d+\. ', '', l), 'desc': '', 'tests': []}
        tiers.append(cur); t = None
    elif l.startswith('## 7'):
        break
    elif l.startswith('#### '):
        t = {'title': l[5:], 'f': {}, 'times': {}}
        cur['tests'].append(t)
    elif t is None and l.startswith('*') and not l.startswith('**') and not l.startswith('* '):
        cur['desc'] = l.strip('*')
    elif t is not None:
        m = re.match(r'\* \*\*(.+?)\*\*:\s*(.*)', l)
        if m:
            t['f'][m.group(1)] = m.group(2)
        m = re.match(r'\s+\* \S+ (Gold|Silver|Bronze): `(.+?)`', l)
        if m:
            t['times'][m.group(1)] = m.group(2)

heads = ['Test', 'Car', 'P/W', 'Engine', 'Drivetrain', 'Track', 'Start', 'Gold', 'Silver', 'Bronze']
for tr in tiers:
    out.append('<h2>%s</h2>' % e(tr['name']))
    if tr['desc']:
        out.append('<p><em>%s</em></p>' % e(tr['desc']))
    out.append('<div class="table-wrapper">\n  <table>\n    <thead>\n      <tr>'
               + ''.join('<th>%s</th>' % h for h in heads)
               + '</tr>\n    </thead>\n    <tbody>')
    for t in tr['tests']:
        f = t['f']; car = f.get('Car', '')
        m = re.match(r'(.*?) \| (\w+)(?: \((\w+)\))? \| ([\d,]+) bhp \| ([\d,]+) kg', car)
        if m:
            name, dt, eng, bhp, kg = m.groups()
            pw = '%.2f kg/hp' % (int(kg.replace(',', '')) / int(bhp.replace(',', '')))
            eng = eng or 'Front'
            carc = md(name)
        else:
            carc = md(car); dt = eng = pw = 'N/A'
        tm = t['times']
        title = t['title']
        title = title.replace(': ', ' - ', 1) if ': ' in title else title
        cells = [e(title), carc, pw, eng, dt,
                 md(f.get('Track / Location', f.get('Track', ''))),
                 md(tex(f.get('Start Type', 'Full Lap'))),
                 tm.get('Gold', ''), tm.get('Silver', ''), tm.get('Bronze', '')]
        out.append('      <tr>' + ''.join('<td>%s</td>' % c for c in cells) + '</tr>')
    out.append('    </tbody>\n  </table>\n</div>')

open('docs/Kunos_Licenses.html', 'w', encoding='utf-8', newline='\r\n').write('\n'.join(out) + '\n')
print(len(tiers), [len(x['tests']) for x in tiers])

