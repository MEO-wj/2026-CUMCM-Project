import re
p = 'paper/main.tex'
txt = open(p, encoding='utf-8').read()
new_abs = open('_tmp/new_abstract.txt', encoding='utf-8').read().strip()
# region between \begin{abstract} and \keywords
start = txt.index('\\begin{abstract}')
kw = txt.index('\\keywords', start)
head = txt[:start] + '\\begin{abstract}\n\n'
tail = txt[kw:]
txt2 = head + new_abs + '\n\n' + tail
assert txt2 != txt, "no change"
open(p, 'w', encoding='utf-8').write(txt2)
print("abstract replaced; new length chars:", len(new_abs))
