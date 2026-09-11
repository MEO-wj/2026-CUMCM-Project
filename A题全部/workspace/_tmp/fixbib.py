data = open('_tmp/bibitems.tex', 'rb').read()
data = data.replace(bytes([92, 105, 98, 105]), bytes([92, 98, 105, 98, 105]))  # \ibi -> \bibi
open('_tmp/bibitems.tex', 'wb').write(data)
print(open('_tmp/bibitems.tex', encoding='utf-8').readlines()[0][:40])
