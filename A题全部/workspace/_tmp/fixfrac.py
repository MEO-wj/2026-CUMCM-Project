import pathlib
p = pathlib.Path('figures/tikz_fvm_mesh.tex')
s = p.read_text(encoding='utf-8')
target = chr(92) + 'frac12'
print('found', s.count(target))
s = s.replace(target, '1/2')
p.write_text(s, encoding='utf-8')
print('remaining', s.count(target))
