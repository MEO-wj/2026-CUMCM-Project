import { Color, DataTexture, DataUtils, HalfFloatType, LinearFilter, LinearSRGBColorSpace, RGBAFormat } from 'three';

export const FIELD_COLORS = {
  temperature: ['#fff2d2', '#ffe0a0', '#ffc26d', '#ff8948', '#ee4029'],
  moisture: ['#e9f6fb', '#b8e5f2', '#58bbe6', '#1479d2', '#0648a6'],
  temperatureSeparated: ['#087ac5', '#42c9f0', '#fff0bd', '#ff8948', '#ee4029'],
};

// Oklab conversion: Björn Ottosson's public-domain reference implementation.
// https://bottosson.github.io/posts/oklab/
function toLab([r, g, b]) {
  const l = Math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b);
  const m = Math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b);
  const s = Math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b);
  return [0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
    1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
    0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s];
}

function fromLab([L, a, b]) {
  const l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3;
  const m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3;
  const s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3;
  return [4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
    -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
    -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s];
}

// Cubic basis adapted from d3-interpolate/src/basis.js (ISC; see notices).
function basis(values, t) {
  const n = values.length - 1;
  const position = Math.max(0, Math.min(1, t)) * n;
  const i = Math.min(n - 1, Math.floor(position));
  const u = position - i, u2 = u * u, u3 = u2 * u;
  const v1 = values[i], v2 = values[i + 1];
  const v0 = i > 0 ? values[i - 1] : 2 * v1 - v2;
  const v3 = i < n - 1 ? values[i + 2] : 2 * v2 - v1;
  return ((1 - 3 * u + 3 * u2 - u3) * v0 + (4 - 6 * u2 + 3 * u3) * v1
    + (1 + 3 * u + 3 * u2 - 3 * u3) * v2 + u3 * v3) / 6;
}

const controls = Object.fromEntries(Object.entries(FIELD_COLORS).map(([field, colors]) => {
  const lab = colors.map((hex) => toLab(new Color(hex).toArray()));
  return [field, [0, 1, 2].map((channel) => lab.map((color) => color[channel]))];
}));

function inGamut(rgb) {
  return rgb.every((value) => value >= -1e-7 && value <= 1.0000001);
}

export function sampleFieldColor(field, value) {
  const lab = controls[field].map((channel) => basis(channel, value));
  let rgb = fromLab(lab);
  if (!inGamut(rgb)) {
    // Preserve lightness and hue by reducing chroma, rather than clipping channels.
    let low = 0, high = 1;
    for (let i = 0; i < 12; i++) {
      const chroma = (low + high) / 2;
      if (inGamut(fromLab([lab[0], lab[1] * chroma, lab[2] * chroma]))) low = chroma;
      else high = chroma;
    }
    rgb = fromLab([lab[0], lab[1] * low, lab[2] * low]);
  }
  return rgb.map((channel) => Math.max(0, Math.min(1, channel)));
}

export const FIELD_GRADIENTS = Object.fromEntries(Object.keys(FIELD_COLORS).map((field) => [field,
  Array.from({ length: 129 }, (_, i) => `#${new Color().fromArray(sampleFieldColor(field, i / 128)).getHexString()}`),
]));

export function createFieldTexture(field) {
  const size = 1024;
  const data = new Uint16Array(size * 4);
  for (let i = 0; i < size; i++) {
    const color = sampleFieldColor(field, i / (size - 1));
    data.set([...color, 1].map((channel) => DataUtils.toHalfFloat(channel)), i * 4);
  }
  const texture = new DataTexture(data, size, 1, RGBAFormat, HalfFloatType);
  texture.colorSpace = LinearSRGBColorSpace;
  texture.minFilter = texture.magFilter = LinearFilter;
  texture.generateMipmaps = false;
  texture.needsUpdate = true;
  return texture;
}
