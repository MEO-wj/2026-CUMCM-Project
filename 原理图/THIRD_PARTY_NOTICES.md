# Third-party notices

## Three.js

This project uses Three.js 0.171.0. Source: https://github.com/mrdoob/three.js/tree/r171

The MIT License

Copyright © 2010-2024 three.js authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

## D3 interpolate

The cubic basis function in `src/colorScale.js` is adapted from d3-interpolate.
Source: https://github.com/d3/d3-interpolate/blob/main/src/basis.js
License: ISC.

Copyright 2010-2021 Mike Bostock

Permission to use, copy, modify, and/or distribute this software for any purpose
with or without fee is hereby granted, provided that the above copyright notice
and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH
REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY SPECIAL, DIRECT,
INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES WHATSOEVER RESULTING FROM LOSS
OF USE, DATA OR PROFITS, WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER
TORTIOUS ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE OF
THIS SOFTWARE.

## Oklab

Oklab conversion formulae follow Björn Ottosson's public-domain reference code:
https://bottosson.github.io/posts/oklab/#converting-from-linear-srgb-to-oklab

## PCSS shadow references

`src/softShadow.js` adapts the blocker-search and contact-hardening approach
from the Three.js PCSS example and the disk-sampling approach in Drei SoftShadows
for an orthographic shadow camera.

- https://github.com/mrdoob/three.js/blob/r171/examples/webgl_shadowmap_pcss.html
- https://github.com/pmndrs/drei/blob/master/src/core/softShadows.tsx
- https://github.com/pmndrs/drei/blob/master/LICENSE

The MIT License text reproduced above also applies to the Drei-derived portion,
with this copyright notice: Copyright (c) 2020 react-spring.

## Material artwork

The medicinal-root surface atlases are generated visual assets made for this
project, not photographs or measured botanical surface data. They depict two
illustrative material directions: a fine-wrinkled fibrous root and a thin-skinned
starchy root. The model geometry, lighting, field colors and annotations are
rendered in code.
