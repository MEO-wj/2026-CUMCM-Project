import os, glob, unicodedata

REPL = {
    'ξ':'xi', 'ρ':'rho', 'σ':'sigma', 'α':'alpha', 'β':'beta',
    'θ':'theta', 'Φ':'Phi', 'φ':'phi', 'μ':'mu', 'τ':'tau', 'Δ':'d',
    '∫':'int', '≈':'~=', '≤':'<=', '≥':'>=', '°':'deg', '²':'^2',
    '·':'*', '×':'x', '→':'->', '←':'<-', '±':'+-', '∞':'inf',
    '§':'sec.', '’':"'", '‘':"'", '“':'"', '”':'"', '—':'-', '–':'-',
    '⛔':'[!]', '√':'sqrt', 'π':'pi', '∂':'d', '∇':'grad',
}

def strip_combining(s):
    # remove combining marks (e.g. D̂ -> D)
    out = []
    for ch in unicodedata.normalize('NFD', s):
        if unicodedata.combining(ch):
            continue
        out.append(ch)
    return ''.join(out)

src = 'code'
dst = '_tmp/code_ascii'
os.makedirs(dst, exist_ok=True)
files = ['params.py','utils.py','problem1.py','problem2.py','problem3.py','problem4.py']
for fn in files:
    p = os.path.join(src, fn)
    if not os.path.exists(p):
        continue
    txt = open(p, encoding='utf-8').read()
    txt = strip_combining(txt)
    for k, v in REPL.items():
        txt = txt.replace(k, v)
    # any remaining non-CJK non-ascii -> '?'; keep CJK (handled by main CJK font? No: listing font lacks CJK too)
    # But CJK in listings uses the CJK fallback via xeCJK; keep CJK, drop other non-ascii
    out = []
    for ch in txt:
        o = ord(ch)
        if o < 128:
            out.append(ch)
        elif 0x4E00 <= o <= 0x9FFF or 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF:
            out.append(ch)  # CJK ideographs / punctuation
        else:
            out.append('?')
    open(os.path.join(dst, fn), 'w', encoding='utf-8').write(''.join(out))
    print('sanitized', fn)
