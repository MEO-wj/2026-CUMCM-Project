import sys, fitz
f = sys.argv[1]
d = fitz.open(f); p = d[0]; pr = p.rect
spans = []
for b in p.get_text("dict")["blocks"]:
    for l in b.get("lines", []):
        for s in l.get("spans", []):
            if s["text"].strip():
                spans.append((fitz.Rect(s["bbox"]), s["text"], s["size"]))
hard = 0; oob = 0
for r, t, _ in spans:
    if r.x0 < pr.x0-0.5 or r.y0 < pr.y0-0.5 or r.x1 > pr.x1+0.5 or r.y1 > pr.y1+0.5:
        oob += 1; print("OOB:", t)
for i in range(len(spans)):
    for j in range(i+1, len(spans)):
        a, b = spans[i][0], spans[j][0]
        it = a & b
        if it.is_empty or it.get_area() <= 0: continue
        m = min(a.get_area(), b.get_area())
        if m > 0 and it.get_area()/m > 0.55:
            hard += 1; print("HARD:", repr(spans[i][1]), "x", repr(spans[j][1]))
sz = sorted(s[2] for s in spans)
p10 = sz[max(0, int(len(sz)*0.10)-0)] if sz else 0
print(f"{f}: spans={len(spans)} min={sz[0]:.2f}pt p10={p10:.2f}pt hard_overlap={hard} oob={oob}")
