import * as THREE from 'three';
import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';
import { createFieldTexture } from './colorScale.js';
import { createSoftShadowMaterial } from './softShadow.js';

export { FIELD_COLORS } from './colorScale.js';

const TAU = Math.PI * 2;
const RADIAL_SEGMENTS = 256;
const MODEL_LENGTH = { whole: 12.5, cutaway: 5.9 };
const SURFACE_TILE_LENGTH = Math.PI; // Two square texture tiles around the nominal circumference.
const SECTION_BORDER = 0.085; // Shared illustrative skin border, not a measured anatomical thickness.
const DEFAULT_SIZE = { whole: [780, 590], cutaway: [420, 300], cross: [480, 480], crossSeparated: [480, 480] };
const VIEW = new THREE.Vector3(-26, 4.4, 9.7).normalize();
const FIELD_VIEW = new THREE.Vector3(-15, 7, 12).normalize();
const LIGHT_POSITIONS = {
  softbox: new THREE.Vector3(-9, 11, 9),
  rim: new THREE.Vector3(7, 6, -10),
};
const APPEARANCES = {
  fibrous: { skinThickness: 0.025, relief: 0.085, sideBump: 0.048, endBump: 0.006, roughness: 0.96, roughnessVariation: 0.12, sheen: 0.10 },
  starchy: { skinThickness: 0.012, relief: 0.052, sideBump: 0.032, endBump: 0.004, roughness: 0.98, roughnessVariation: 0.06, sheen: 0.03 },
};
const WINDOW_CURVE_GLSL = `
  float windowBend(float v) {
    float arch = sin(3.14159265359 * v);
    return 0.20 * sin(6.28318530718 * v) * arch + 0.035 * arch * arch;
  }
`;

function windowBoundary(angle, v) {
  const arch = Math.sin(Math.PI * v);
  return angle + 0.20 * Math.sin(TAU * v) * arch + 0.035 * arch * arch;
}

function textureDrift(axialTiles) {
  return 0.09 * Math.sin(axialTiles * 0.83) + 0.025 * Math.sin(axialTiles * 1.79 + 0.7);
}

function softenTileSeams(canvas) {
  const context = canvas.getContext('2d', { willReadFrequently: true });
  const { width, height } = canvas;
  const image = context.getImageData(0, 0, width, height);
  let pixels = image.data;
  // Blend only narrow opposite edge strips. The root fibres themselves are never mirrored.
  for (const axis of ['x', 'y']) {
    const output = new Uint8ClampedArray(pixels);
    const extent = axis === 'x' ? width : height;
    const feather = Math.round(extent * 0.035);
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const position = axis === 'x' ? x : y;
        const distance = Math.min(position, extent - 1 - position);
        if (distance >= feather) continue;
        const t = distance / feather;
        const blend = 0.5 * (1 - t * t * (3 - 2 * t));
        const otherX = axis === 'x' ? width - 1 - x : x;
        const otherY = axis === 'y' ? height - 1 - y : y;
        const i = (y * width + x) * 4, other = (otherY * width + otherX) * 4;
        for (let channel = 0; channel < 3; channel++) {
          output[i + channel] = pixels[i + channel] * (1 - blend) + pixels[other + channel] * blend;
        }
      }
    }
    pixels = output;
  }
  image.data.set(pixels);
  context.putImageData(image, 0, 0);
}

function atlasPanel(image, side) {
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1024;
  const halfWidth = image.width / 2;
  canvas.getContext('2d', { willReadFrequently: true }).drawImage(image, side * halfWidth, 0, halfWidth, image.height, 0, 0, 1024, 1024);
  const color = new THREE.CanvasTexture(canvas);
  color.colorSpace = THREE.SRGBColorSpace;
  color.minFilter = THREE.LinearMipmapLinearFilter;
  color.magFilter = THREE.LinearFilter;
  return { canvas, color };
}

function estimateMicroRelief(source, roughnessVariation = 0.04) {
  // A rendering estimate from high-frequency albedo contrast, not a measured height/normal map.
  // Subtracting the local mean prevents broad color patches and baked illumination becoming pits.
  const size = 512, stride = size + 1;
  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = size;
  const context = canvas.getContext('2d', { willReadFrequently: true });
  context.drawImage(source, 0, 0, size, size);
  const pixels = context.getImageData(0, 0, size, size).data;
  const luminance = new Float32Array(size * size);
  const integral = new Float64Array(stride * stride);
  const linear = Array.from({ length: 256 }, (_, i) => {
    const c = i / 255;
    return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  const mean = new THREE.Color(0, 0, 0);
  for (let y = 0; y < size; y++) {
    let row = 0;
    for (let x = 0; x < size; x++) {
      const i = (y * size + x) * 4;
      const r = linear[pixels[i]], g = linear[pixels[i + 1]], b = linear[pixels[i + 2]];
      mean.r += r; mean.g += g; mean.b += b;
      const value = r * 0.2126 + g * 0.7152 + b * 0.0722;
      luminance[y * size + x] = value;
      row += value;
      integral[(y + 1) * stride + x + 1] = integral[y * stride + x + 1] + row;
    }
  }
  mean.multiplyScalar(1 / (size * size));
  const height = new Float32Array(size * size);
  const output = context.createImageData(size, size);
  const roughnessData = new Uint8Array(size * size * 4);
  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const x0 = Math.max(0, x - 8), x1 = Math.min(size, x + 9);
      const y0 = Math.max(0, y - 8), y1 = Math.min(size, y + 9);
      const sum = integral[y1 * stride + x1] - integral[y0 * stride + x1]
        - integral[y1 * stride + x0] + integral[y0 * stride + x0];
      const local = sum / ((x1 - x0) * (y1 - y0));
      const value = THREE.MathUtils.clamp(0.5 + (luminance[y * size + x] - local) * 2.8, 0.22, 0.78);
      height[y * size + x] = value;
      const gray = Math.round(value * 255);
      output.data.set([gray, gray, gray, 255], (y * size + x) * 4);
      const matte = Math.round(255 * THREE.MathUtils.clamp(0.96 + (0.5 - value) / 0.28 * roughnessVariation, 0.80, 1.0));
      roughnessData.set([matte, matte, matte, 255], (y * size + x) * 4);
    }
  }
  context.putImageData(output, 0, 0);
  const bump = new THREE.CanvasTexture(canvas);
  bump.colorSpace = THREE.NoColorSpace;
  bump.minFilter = THREE.LinearMipmapLinearFilter;
  bump.magFilter = THREE.LinearFilter;
  const roughnessCanvas = document.createElement('canvas');
  roughnessCanvas.width = roughnessCanvas.height = size;
  roughnessCanvas.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(roughnessData), size, size), 0, 0);
  const roughness = new THREE.CanvasTexture(roughnessCanvas);
  roughness.minFilter = THREE.LinearMipmapLinearFilter;
  roughness.magFilter = THREE.LinearFilter;
  roughness.generateMipmaps = true;
  roughness.needsUpdate = true;
  return { bump, roughness, height, size, mean };
}

async function loadRootAppearance(name) {
  const settings = APPEARANCES[name];
  // Generated schematic material atlas: left = longitudinal skin; right = cut-end albedo.
  const image = await new THREE.ImageLoader().loadAsync(`${import.meta.env.BASE_URL}textures/root-${name}.png`);
  const side = atlasPanel(image, 0), end = atlasPanel(image, 1);
  softenTileSeams(side.canvas);
  const sideRelief = estimateMicroRelief(side.canvas, settings.roughnessVariation);
  const endRelief = estimateMicroRelief(end.canvas, settings.roughnessVariation * 0.4);
  for (const texture of [side.color, sideRelief.bump, sideRelief.roughness]) {
    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(2, 1);
  }
  const radiusAt = (theta, axialTiles) => {
    const u = THREE.MathUtils.euclideanModulo(theta / TAU * 2 + textureDrift(axialTiles), 1);
    const v = THREE.MathUtils.euclideanModulo(axialTiles, 1);
    const x = u * sideRelief.size - 0.5, y = (1 - v) * sideRelief.size - 0.5;
    const xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi;
    const sample = (px, py) => sideRelief.height[THREE.MathUtils.euclideanModulo(py, sideRelief.size) * sideRelief.size + THREE.MathUtils.euclideanModulo(px, sideRelief.size)];
    const h = THREE.MathUtils.lerp(
      THREE.MathUtils.lerp(sample(xi, yi), sample(xi + 1, yi), fx),
      THREE.MathUtils.lerp(sample(xi, yi + 1), sample(xi + 1, yi + 1), fx), fy,
    );
    // Keep the same envelope at the side, end ring and window lip, with clearance for the inner surface.
    return Math.max(1 - settings.skinThickness + 0.004, 1 + (h - 0.5) * settings.relief);
  };
  return { settings, side, end, sideRelief, endRelief, radiusAt };
}

function makeRootMaterial(panel, relief, settings, strength, isEnd = false) {
  const bumpScale = isEnd ? settings.endBump : settings.sideBump;
  const material = new THREE.MeshPhysicalMaterial({
    map: panel.color, bumpMap: relief.bump, bumpScale,
    roughnessMap: relief.roughness,
    roughness: settings.roughness, metalness: 0, side: THREE.DoubleSide,
    clearcoat: 0, transmission: 0, specularIntensity: 0.28,
    sheen: isEnd ? 0 : settings.sheen, sheenRoughness: 0.94, sheenColor: relief.mean.clone(),
  });
  material.userData.baseBumpScale = bumpScale;
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uTextureStrength = strength;
    shader.uniforms.uMeanColor = { value: relief.mean };
    shader.fragmentShader = `uniform float uTextureStrength; uniform vec3 uMeanColor;\n${shader.fragmentShader}`;
    shader.fragmentShader = shader.fragmentShader.replace('#include <map_fragment>', `
      #include <map_fragment>
      diffuseColor.rgb = max(vec3(0.0), mix(uMeanColor, diffuseColor.rgb, uTextureStrength));
    `);
  };
  material.customProgramCacheKey = () => 'root-albedo-r171';
  return material;
}

function makeFieldMaterial(mode, stage, fields, detail = null, radius = 1) {
  return new THREE.ShaderMaterial({
    side: THREE.DoubleSide,
    toneMapped: false,
    uniforms: {
      uStage: stage,
      uBody: { value: mode === 'body' ? 1 : 0 },
      uRadius: { value: radius },
      uViewDirection: { value: VIEW.clone() },
      uKeyLightPosition: { value: LIGHT_POSITIONS.softbox.clone() },
      uRimLightDirection: { value: LIGHT_POSITIONS.rim.clone().normalize() },
      uTemperature: { value: mode === 'separatedDisk' ? fields.temperatureSeparated : fields.temperature },
      uMoisture: { value: fields.moisture },
      uDetail: { value: detail },
      uDetailStrength: { value: detail ? 0.095 : 0 },
      uCreamLab: { value: new THREE.Vector3(0.954703768, -0.004256932, 0.067294496) }, // #fff0bd
      uCyanLab: { value: new THREE.Vector3(0.779891783, -0.094127263, -0.083051642) }, // #42c9f0
    },
    vertexShader: `
      varying vec2 vFieldUv;
      varying vec3 vFieldPosition;
      varying vec3 vFieldNormal;
      void main() {
        vFieldUv = uv;
        vFieldPosition = position;
        vFieldNormal = normal;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform int uStage;
      uniform int uBody;
      uniform float uRadius;
      uniform vec3 uViewDirection;
      uniform vec3 uKeyLightPosition;
      uniform vec3 uRimLightDirection;
      uniform sampler2D uTemperature;
      uniform sampler2D uMoisture;
      uniform sampler2D uDetail;
      uniform float uDetailStrength;
      uniform vec3 uCreamLab;
      uniform vec3 uCyanLab;
      varying vec2 vFieldUv;
      varying vec3 vFieldPosition;
      varying vec3 vFieldNormal;
      vec3 ramp(float value, bool temperature) {
        float u = (clamp(value, 0.0, 1.0) * 1023.0 + 0.5) / 1024.0;
        return temperature ? texture2D(uTemperature, vec2(u, 0.5)).rgb : texture2D(uMoisture, vec2(u, 0.5)).rgb;
      }
      // Oklab transforms: Björn Ottosson's public-domain reference implementation.
      // https://bottosson.github.io/posts/oklab/
      vec3 toOklab(vec3 rgb) {
        vec3 lms = vec3(
          dot(rgb, vec3(0.4122214708, 0.5363325363, 0.0514459929)),
          dot(rgb, vec3(0.2119034982, 0.6806995451, 0.1073969566)),
          dot(rgb, vec3(0.0883024619, 0.2817188376, 0.6299787005))
        );
        lms = pow(max(lms, vec3(0.0)), vec3(1.0 / 3.0));
        return vec3(
          dot(lms, vec3(0.2104542553, 0.7936177850, -0.0040720468)),
          dot(lms, vec3(1.9779984951, -2.4285922050, 0.4505937099)),
          dot(lms, vec3(0.0259040371, 0.7827717662, -0.8086757660))
        );
      }
      vec3 fromOklab(vec3 lab) {
        vec3 lms = vec3(
          dot(lab, vec3(1.0, 0.3963377774, 0.2158037573)),
          dot(lab, vec3(1.0, -0.1055613458, -0.0638541728)),
          dot(lab, vec3(1.0, -0.0894841775, -1.2914855480))
        );
        lms = lms * lms * lms;
        return vec3(
          dot(lms, vec3(4.0767416621, -3.3077115913, 0.2309699292)),
          dot(lms, vec3(-1.2684380046, 2.6097574011, -0.3413193965)),
          dot(lms, vec3(-0.0041960863, -0.7034186147, 1.7076147010))
        );
      }
      bool inGamut(vec3 color) {
        return all(greaterThanEqual(color, vec3(0.0))) && all(lessThanEqual(color, vec3(1.0)));
      }
      vec3 perceptualComposite(vec3 warm, vec3 wetBlue, float t) {
        vec3 a = toOklab(warm), d = toOklab(wetBlue);
        // One cubic passes through cream and cyan at t=1/3 and 2/3, without piecewise plateaus.
        vec3 b = 3.0 * uCreamLab - 1.5 * uCyanLab - (5.0 / 6.0) * a + d / 3.0;
        vec3 c = 3.0 * uCyanLab - 1.5 * uCreamLab + a / 3.0 - (5.0 / 6.0) * d;
        float u = 1.0 - t;
        vec3 lab = u*u*u*a + 3.0*u*u*t*b + 3.0*u*t*t*c + t*t*t*d;
        vec3 color = fromOklab(lab);
        if (inGamut(color)) return color;
        // Preserve the curve's lightness and hue, reducing only chroma when a color leaves sRGB.
        float low = 0.0, high = 1.0;
        for (int i = 0; i < 10; i++) {
          float chroma = (low + high) * 0.5;
          if (inGamut(fromOklab(vec3(lab.x, lab.yz * chroma)))) low = chroma;
          else high = chroma;
        }
        return clamp(fromOklab(vec3(lab.x, lab.yz * low)), 0.0, 1.0);
      }
      void main() {
        vec2 p = vFieldUv * 2.0 - 1.0;
        float r = clamp(length(p), 0.0, 1.0);
        if (uBody == 1) {
          // Analytic qualitative X-ray: use the closest point on the viewing ray to the cylinder axis.
          // End caps retain their actual radial field. No ray-marching or numeric physics is implied.
          vec2 ray = normalize(uViewDirection.yz);
          vec2 closest = vFieldPosition.yz - ray * dot(vFieldPosition.yz, ray);
          r = clamp((abs(vFieldNormal.x) > 0.5 ? length(vFieldPosition.yz) : length(closest)) / uRadius, 0.0, 1.0);
        }
        float temperature = uStage == 0 ? 0.16 : (uStage == 1 ? 0.12 + 0.84 * r * r : 0.50 + 0.46 * r * r);
        float moisture = uStage == 0 ? 0.86 : (uStage == 1 ? 0.84 - 0.70 * r * r : 0.28 - 0.13 * r * r);
        // Two scalar fields remain distinct. Optical path affects only the visibility of the water layer.
        // In particular, both initial scalar fields are constant despite the optical blue-core appearance.
        float opticalPath = sqrt(max(0.0, 1.0 - r * r));
        float waterLayer = 1.0 - exp(-3.4 * moisture * moisture * opticalPath);
        // The final-stage visual preset is already warm; residual moisture must not whiten its core.
        if (uStage == 2) waterLayer *= 0.10;
        vec3 composite = ${mode === 'separatedDisk'
          ? 'p.y > 0.0 ? ramp(temperature, true) : ramp(moisture, false)'
          : 'perceptualComposite(ramp(temperature, true), ramp(moisture, false), waterLayer)'};
        gl_FragColor = vec4(composite, 1.0);
        vec2 detailUv = uBody == 1 ? vec2(vFieldUv.y * 3.5, vFieldUv.x) : vFieldUv;
        detailUv = 1.0 - abs(mod(detailUv, 2.0) - 1.0);
        float microRelief = texture2D(uDetail, detailUv).r;
        gl_FragColor.rgb *= 1.0 + clamp((microRelief - 0.5) * uDetailStrength / 0.28, -uDetailStrength, uDetailStrength);
        // Restrained GDC 2011 / Three.js SubsurfaceScatteringShader-style lighting approximation.
        // Actual surface normals and scene light directions modulate only radiance, never T, C or waterLayer.
        vec3 normal = normalize(vFieldNormal);
        vec3 keyDirection = normalize(uKeyLightPosition - vFieldPosition);
        float wrappedDiffuse = clamp((dot(normal, keyDirection) + 0.2) / 1.2, 0.0, 1.0);
        vec3 scatteringHalf = normalize(uRimLightDirection + normal * 0.18);
        float scatteringPhase = pow(max(dot(normalize(uViewDirection), -scatteringHalf), 0.0), 2.0);
        float normalizedThickness = 0.15 + 0.85 * opticalPath;
        float backScatter = scatteringPhase * exp(-2.3 * normalizedThickness);
        gl_FragColor.rgb *= 1.0 + 0.05 * (wrappedDiffuse - 0.5) + 0.03 * backScatter;
        #include <colorspace_fragment>
        float dither = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453) - 0.5;
        gl_FragColor.rgb = clamp(gl_FragColor.rgb + dither / 255.0, 0.0, 1.0);
      }
    `,
  });
}

function makeSide(length, start, arc, radiusAt) {
  const radialSegments = Math.max(3, Math.round(RADIAL_SEGMENTS * arc / TAU));
  const lengthSegments = Math.ceil(length * 20);
  const positions = [], uvs = [], indices = [];
  for (let i = 0; i <= lengthSegments; i++) {
    const v = i / lengthSegments;
    const axialTiles = v * length / SURFACE_TILE_LENGTH;
    for (let j = 0; j <= radialSegments; j++) {
      const theta = start + j / radialSegments * arc;
      const radius = radiusAt(theta, v);
      positions.push((v - 0.5) * length, radius * Math.cos(theta), radius * Math.sin(theta));
      uvs.push(theta / TAU + textureDrift(axialTiles) / 2, axialTiles);
      if (i < lengthSegments && j < radialSegments) {
        const a = i * (radialSegments + 1) + j;
        const b = a + radialSegments + 1;
        indices.push(a, a + 1, b, b, a + 1, b + 1);
      }
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function makeCap(radius, start = 0, arc = TAU) {
  const segments = Math.max(3, Math.round(RADIAL_SEGMENTS * arc / TAU));
  const positions = [0, 0, 0], uvs = [0.5, 0.5], indices = [];
  for (let i = 0; i <= segments; i++) {
    const theta = start + i / segments * arc;
    const y = radius * Math.cos(theta);
    const z = radius * Math.sin(theta);
    positions.push(0, y, z);
    uvs.push(z / (2 * radius) + 0.5, y / (2 * radius) + 0.5);
    if (i > 0) indices.push(0, i + 1, i);
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function makeCapRim(start, arc, surfaceEnd, radiusAt, innerRadius) {
  const positions = [], uvs = [], indices = [];
  for (let i = 0; i <= RADIAL_SEGMENTS; i++) {
    const theta = start + i / RADIAL_SEGMENTS * arc;
    for (const r of [innerRadius, radiusAt(theta, surfaceEnd)]) {
      const y = r * Math.cos(theta), z = r * Math.sin(theta);
      positions.push(0, y, z);
      uvs.push(z / 2 + 0.5, y / 2 + 0.5);
    }
    if (i < RADIAL_SEGMENTS) {
      const a = i * 2;
      indices.push(a, a + 2, a + 1, a + 1, a + 2, a + 3);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function makeWindowLip(length, angle, radiusAt, innerRadius) {
  const segments = Math.ceil(length * 20);
  const positions = [], uvs = [], indices = [];
  for (let i = 0; i <= segments; i++) {
    const v = i / segments;
    const boundary = windowBoundary(angle, v);
    for (const [theta, radius] of [
      [boundary - 0.008, radiusAt(boundary - 0.008, v)],
      [boundary + 0.022, innerRadius + 0.002],
    ]) {
      positions.push((v - 0.5) * length, radius * Math.cos(theta), radius * Math.sin(theta));
      uvs.push(theta / TAU, v);
    }
    if (i < segments) {
      const a = i * 2;
      indices.push(a, a + 1, a + 2, a + 1, a + 3, a + 2);
    }
  }
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return geometry;
}

function makeWhole(skinMaterial, endMaterial, radiusAt, skinThickness) {
  const group = new THREE.Group();
  const length = MODEL_LENGTH.whole; // Diameter is 2: the specimen retains L / D = 6.25.
  const side = new THREE.Mesh(makeSide(length, 0, TAU, radiusAt), skinMaterial);
  side.castShadow = side.receiveShadow = true;
  group.add(side);
  group.userData.lengthRings = {
    mesh: side,
    backStart: side.geometry.attributes.position.count - RADIAL_SEGMENTS - 1,
  };
  for (const sign of [-1, 1]) {
    const innerRadius = 1 - skinThickness;
    const end = sign < 0 ? 0 : 1;
    const cap = new THREE.Mesh(makeCap(innerRadius), endMaterial);
    cap.position.x = sign * length / 2;
    cap.castShadow = cap.receiveShadow = true;
    group.add(cap);
    const skin = new THREE.Mesh(makeCapRim(0, TAU, end, radiusAt, innerRadius), skinMaterial);
    skin.position.x = sign * length / 2;
    skin.castShadow = skin.receiveShadow = true;
    group.add(skin);
  }
  group.userData.anchors = {
    frontCenter: new THREE.Vector3(-length / 2, 0, 0),
    backCenter: new THREE.Vector3(length / 2, 0, 0),
    radiusEnd: new THREE.Vector3(-length / 2, radiusAt(0, 0), 0),
  };
  return group;
}

function makeSurfaceFlows(length, radiusAt) {
  const view = new THREE.Vector2(FIELD_VIEW.y, FIELD_VIEW.z).normalize();
  const top = new THREE.Vector2(view.y, -view.x);
  const flows = { heat: [], water: [] };
  const point = (fraction, theta, radius) => {
    const surfaceRadius = radiusAt(theta, fraction + 0.5);
    return new THREE.Vector3(fraction * length, Math.cos(theta) * surfaceRadius * radius, Math.sin(theta) * surfaceRadius * radius);
  };
  for (const sign of [1, -1]) {
    const radial = top.clone().multiplyScalar(sign * Math.cos(Math.PI / 12))
      .addScaledVector(view, Math.sin(Math.PI / 12)).normalize();
    const theta = Math.atan2(radial.y, radial.x);
    for (const fraction of [-0.32, 0, 0.32]) {
      flows.heat.push([point(fraction, theta, 1.7), point(fraction, theta, 1.02)]);
    }
    const waterPositions = sign > 0 ? [-0.17, 0.19] : [-0.14, 0.22];
    for (const fraction of waterPositions) {
      flows.water.push([point(fraction, theta, 1.01), point(fraction, theta, 1.8)]);
    }
  }
  return flows;
}

function makeCutaway(skinMaterial, endMaterial, stage, radiusAt, fields, detail) {
  const group = new THREE.Group();
  const length = MODEL_LENGTH.cutaway; // Shortened schematic; only the whole specimen uses the physical L/D ratio.
  const innerRadius = 1 - SECTION_BORDER;
  const recess = 0.045;
  const radialView = new THREE.Vector2(FIELD_VIEW.y, FIELD_VIEW.z).normalize();
  const topDirection = new THREE.Vector2(radialView.y, -radialView.x);
  const thetaUp = Math.atan2(topDirection.y, topDirection.x);
  const boundaryAngle = Math.atan2(radialView.y, radialView.x);
  const volume = new THREE.Mesh(
    new THREE.CylinderGeometry(innerRadius, innerRadius, length - recess * 2, RADIAL_SEGMENTS, 32, false).rotateZ(-Math.PI / 2),
    makeFieldMaterial('body', stage, fields, detail, innerRadius),
  );
  volume.castShadow = true;
  group.add(volume);

  // The narrow feather follows a shallow fibre-aligned S curve; most of the natural skin stays fully opaque.
  const curvedSkin = skinMaterial.clone();
  curvedSkin.transparent = true;
  curvedSkin.depthWrite = false;
  curvedSkin.side = THREE.FrontSide;
  curvedSkin.onBeforeCompile = (shader) => {
    skinMaterial.onBeforeCompile(shader);
    shader.uniforms.uSkinLength = { value: length };
    shader.uniforms.uBoundaryAngle = { value: boundaryAngle };
    shader.vertexShader = `varying vec3 vSkinPosition;\n${shader.vertexShader}`;
    shader.vertexShader = shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n vSkinPosition = position;');
    shader.fragmentShader = `varying vec3 vSkinPosition; uniform float uSkinLength; uniform float uBoundaryAngle;\n${WINDOW_CURVE_GLSL}\n${shader.fragmentShader}`;
    shader.fragmentShader = shader.fragmentShader.replace('#include <opaque_fragment>', `
      float along = clamp(vSkinPosition.x / uSkinLength + 0.5, 0.0, 1.0);
      float boundary = uBoundaryAngle + windowBend(along);
      float windowSide = sin(atan(vSkinPosition.z, vSkinPosition.y) - boundary);
      diffuseColor.a *= 1.0 - smoothstep(-0.09, 0.12, windowSide);
      #include <opaque_fragment>
    `);
  };
  curvedSkin.customProgramCacheKey = () => 'root-curved-half-window-r171';
  const shell = new THREE.Mesh(makeSide(length, 0, TAU, radiusAt), curvedSkin);
  shell.renderOrder = 2;
  shell.castShadow = shell.receiveShadow = true;
  // The X-ray window is a display treatment. Its physical outer silhouette remains opaque to the shadow pass.
  shell.customDepthMaterial = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, side: THREE.DoubleSide });
  group.add(shell);
  // The opposite side keeps a thin continuous natural silhouette around the viewing window.
  const edgeHalfAngle = Math.acos(innerRadius);
  const underside = new THREE.Mesh(makeSide(length, thetaUp + Math.PI - edgeHalfAngle, edgeHalfAngle * 2, radiusAt), skinMaterial);
  underside.castShadow = underside.receiveShadow = true;
  group.add(underside);
  for (const sign of [-1, 1]) {
    const edge = new THREE.Mesh(makeCapRim(0, TAU, sign < 0 ? 0 : 1, radiusAt, innerRadius), skinMaterial);
    edge.position.x = sign * length / 2;
    edge.castShadow = edge.receiveShadow = true;
    group.add(edge);
    const innerWall = new THREE.Mesh(
      new THREE.CylinderGeometry(innerRadius, innerRadius, recess, RADIAL_SEGMENTS, 1, true).rotateZ(-Math.PI / 2),
      skinMaterial,
    );
    innerWall.position.x = sign * (length / 2 - recess / 2);
    innerWall.castShadow = innerWall.receiveShadow = true;
    group.add(innerWall);
  }
  const lipMaterial = endMaterial.clone();
  lipMaterial.onBeforeCompile = endMaterial.onBeforeCompile;
  lipMaterial.customProgramCacheKey = endMaterial.customProgramCacheKey;
  lipMaterial.color.set('#f0e5cf');
  lipMaterial.transparent = true;
  lipMaterial.opacity = 0.35;
  lipMaterial.depthWrite = false;
  const lip = new THREE.Mesh(makeWindowLip(length, boundaryAngle, radiusAt, innerRadius), lipMaterial);
  lip.renderOrder = 3;
  lip.castShadow = lip.receiveShadow = true;
  group.add(lip);
  const windowMaterial = new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.FrontSide, toneMapped: false,
    uniforms: {
      uDetail: { value: detail },
      uRay: { value: new THREE.Vector2(FIELD_VIEW.y, FIELD_VIEW.z).normalize() },
      uFrameRadius: { value: innerRadius },
      uBoundaryAngle: { value: boundaryAngle },
      uSkinLength: { value: length },
    },
    vertexShader: `
      varying vec3 vPosition;
      varying vec3 vNormal;
      varying vec2 vUv;
      void main() {
        vPosition = position; vNormal = normal; vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform sampler2D uDetail;
      uniform vec2 uRay;
      uniform float uFrameRadius;
      uniform float uBoundaryAngle;
      uniform float uSkinLength;
      varying vec3 vPosition;
      varying vec3 vNormal;
      varying vec2 vUv;
      ${WINDOW_CURVE_GLSL}
      void main() {
        vec2 closest = vPosition.yz - uRay * dot(vPosition.yz, uRay);
        float edge = abs(vNormal.x) > 0.5 ? length(vPosition.yz) : length(closest);
        vec2 uv = abs(vNormal.x) > 0.5 ? vUv : vec2(vUv.y * 3.2 + 0.04, vUv.x + 0.02);
        uv = 1.0 - abs(mod(uv, 2.0) - 1.0);
        float textureDetail = texture2D(uDetail, uv).r - 0.5;
        float along = clamp(vPosition.x / uSkinLength + 0.5, 0.0, 1.0);
        float boundary = uBoundaryAngle + windowBend(along);
        float windowSide = sin(atan(vPosition.z, vPosition.y) - boundary);
        float visibleWindow = abs(vNormal.x) > 0.5 ? 1.0 : smoothstep(-0.08, 0.14, windowSide);
        float aperture = (1.0 - smoothstep(uFrameRadius - 0.025, uFrameRadius + 0.008, edge)) * visibleWindow;
        float veil = 0.012 + abs(textureDetail) * 0.055;
        gl_FragColor = vec4(vec3(textureDetail >= 0.0 ? 1.0 : 0.1), aperture * veil);
        #include <colorspace_fragment>
      }
    `,
  });
  const windowMesh = new THREE.Mesh(
    new THREE.CylinderGeometry(0.997, 0.997, length - 0.005, RADIAL_SEGMENTS, 24, false).rotateZ(-Math.PI / 2),
    windowMaterial,
  );
  windowMesh.renderOrder = 3;
  group.add(windowMesh);
  group.userData.anchors = {
    frontCenter: new THREE.Vector3(-length / 2, 0, 0),
    backCenter: new THREE.Vector3(length / 2, 0, 0),
    radiusEnd: new THREE.Vector3(-length / 2, radiusAt(0, 0), 0),
  };
  group.userData.surfaceFlows = makeSurfaceFlows(length, radiusAt);
  group.userData.framingPoints = Object.values(group.userData.surfaceFlows).flat(2);
  return group;
}

function makeCross(skinMaterial, stage, fields, detail, separated = false) {
  const group = new THREE.Group();
  const innerRadius = 1 - SECTION_BORDER;
  const field = new THREE.Mesh(new THREE.CircleGeometry(innerRadius + 0.0003, RADIAL_SEGMENTS), makeFieldMaterial(separated ? 'separatedDisk' : 'disk', stage, fields, detail));
  // Disk UVs cover the field radius itself, so r = 1 denotes its outer boundary.
  group.add(field);
  const ring = new THREE.Mesh(new THREE.RingGeometry(innerRadius, 1, RADIAL_SEGMENTS), skinMaterial);
  ring.position.z = 0.006;
  group.add(ring);
  const border = new THREE.Mesh(new THREE.RingGeometry(innerRadius - 0.0015, innerRadius + 0.0015, RADIAL_SEGMENTS), new THREE.MeshBasicMaterial({ color: '#ad895c' }));
  border.position.z = 0.01;
  group.add(border);
  group.userData.anchors = {
    frontCenter: new THREE.Vector3(), backCenter: new THREE.Vector3(), radiusEnd: new THREE.Vector3(0, 1, 0),
  };
  return group;
}

function makeAppearanceModels(appearance, strength, stage, fields) {
  const { settings, side, end, sideRelief, endRelief, radiusAt } = appearance;
  const wholeRadiusAt = (theta, v) => radiusAt(theta, v * MODEL_LENGTH.whole / SURFACE_TILE_LENGTH);
  const processRadiusAt = (theta, v) => radiusAt(theta, v * MODEL_LENGTH.cutaway / SURFACE_TILE_LENGTH);
  const sideMaterial = makeRootMaterial(side, sideRelief, settings, strength);
  const endMaterial = makeRootMaterial(end, endRelief, settings, strength, true);
  return {
    textures: [side.color, sideRelief.bump, sideRelief.roughness, end.color, endRelief.bump, endRelief.roughness],
    groups: {
      whole: makeWhole(sideMaterial, endMaterial, wholeRadiusAt, settings.skinThickness),
      cutaway: makeCutaway(sideMaterial, endMaterial, stage, processRadiusAt, fields, endRelief.bump),
      cross: makeCross(sideMaterial, stage, fields, endRelief.bump),
      crossSeparated: makeCross(sideMaterial, stage, fields, endRelief.bump, true),
    },
  };
}

function frameObject(camera, object, width, height, occupancy) {
  object.updateMatrixWorld(true);
  camera.updateMatrixWorld(true);
  const bounds = new THREE.Box3();
  const point = new THREE.Vector3();
  object.traverse((child) => {
    const positions = child.geometry?.attributes.position;
    if (!positions) return;
    for (let i = 0; i < positions.count; i++) {
      point.fromBufferAttribute(positions, i).applyMatrix4(child.matrixWorld).applyMatrix4(camera.matrixWorldInverse);
      bounds.expandByPoint(point);
    }
  });
  for (const anchor of object.userData.framingPoints ?? []) {
    point.copy(anchor).applyMatrix4(object.matrixWorld).applyMatrix4(camera.matrixWorldInverse);
    bounds.expandByPoint(point);
  }
  const size = bounds.getSize(new THREE.Vector3());
  const center = bounds.getCenter(new THREE.Vector3());
  const aspect = width / height;
  const viewHeight = Math.max(size.y, size.x / aspect) / occupancy;
  camera.left = center.x - viewHeight * aspect / 2;
  camera.right = center.x + viewHeight * aspect / 2;
  camera.top = center.y + viewHeight / 2;
  camera.bottom = center.y - viewHeight / 2;
  camera.updateProjectionMatrix();
  return {
    minX: (bounds.min.x - camera.left) / (camera.right - camera.left) * width,
    maxX: (bounds.max.x - camera.left) / (camera.right - camera.left) * width,
    minY: (camera.top - bounds.max.y) / (camera.top - camera.bottom) * height,
    maxY: (camera.top - bounds.min.y) / (camera.top - camera.bottom) * height,
  };
}

function makeGroundShadow() {
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(1, 1, 4, 4), createSoftShadowMaterial());
  mesh.rotation.x = -Math.PI / 2;
  mesh.receiveShadow = true;
  return mesh;
}

function fitGroundShadow(scene, object, receiver, light) {
  scene.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(object);
  const size = box.getSize(new THREE.Vector3());
  const groundY = box.min.y - 0.002;
  const lightPosition = light.getWorldPosition(new THREE.Vector3());
  const target = light.target.getWorldPosition(new THREE.Vector3());
  const direction = lightPosition.clone().sub(target).normalize();
  const corners = [], projections = [];
  const shadowBox = new THREE.Box3();
  for (const x of [box.min.x, box.max.x]) {
    for (const y of [box.min.y, box.max.y]) {
      for (const z of [box.min.z, box.max.z]) {
        const corner = new THREE.Vector3(x, y, z);
        const projection = corner.clone().addScaledVector(direction, -(y - groundY) / direction.y);
        corners.push(corner);
        projections.push(projection);
        shadowBox.expandByPoint(projection);
      }
    }
  }
  const shadowSize = shadowBox.getSize(new THREE.Vector3());
  const shadowCenter = shadowBox.getCenter(new THREE.Vector3());
  const padding = Math.max(0.35, size.y * 0.5);
  receiver.position.set(shadowCenter.x, groundY, shadowCenter.z);
  receiver.scale.set(shadowSize.x + padding * 2, shadowSize.z + padding * 2, 1);
  receiver.updateMatrixWorld(true);
  const shadowCamera = light.shadow.camera;
  shadowCamera.position.copy(lightPosition);
  shadowCamera.lookAt(target);
  shadowCamera.updateMatrixWorld(true);
  const lightBounds = new THREE.Box3();
  const lightPoints = [...corners, ...projections];
  for (const x of [shadowBox.min.x - padding, shadowBox.max.x + padding]) {
    for (const z of [shadowBox.min.z - padding, shadowBox.max.z + padding]) lightPoints.push(new THREE.Vector3(x, groundY, z));
  }
  for (const point of lightPoints) lightBounds.expandByPoint(point.clone().applyMatrix4(shadowCamera.matrixWorldInverse));
  shadowCamera.left = lightBounds.min.x - 0.2;
  shadowCamera.right = lightBounds.max.x + 0.2;
  shadowCamera.bottom = lightBounds.min.y - 0.2;
  shadowCamera.top = lightBounds.max.y + 0.2;
  shadowCamera.near = Math.max(0.1, -lightBounds.max.z - 0.5);
  shadowCamera.far = Math.max(shadowCamera.near + 1, -lightBounds.min.z + 0.5);
  shadowCamera.updateProjectionMatrix();
  const uniforms = receiver.material.uniforms;
  uniforms.uShadowMatrix.value = light.shadow.matrix;
  uniforms.uMapSize.value.copy(light.shadow.mapSize);
  uniforms.uFrustum.value.set(shadowCamera.right - shadowCamera.left, shadowCamera.top - shadowCamera.bottom);
  uniforms.uDepthRange.value = shadowCamera.far - shadowCamera.near;
  uniforms.uSearchGap.value = size.y / Math.max(0.1, direction.y);
  uniforms.uBias.value = light.shadow.bias;
  receiver.onBeforeRender = () => {
    uniforms.uDepthMap.value = light.shadow.map?.texture ?? null;
    receiver.material.uniformsNeedUpdate = true;
  };
  light.shadow.needsUpdate = true;
}

export async function createHerbRenderer() {
  RectAreaLightUniformsLib.init();
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.setClearColor(0x000000, 0);
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFShadowMap;
  const scene = new THREE.Scene();
  const camera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.1, 100);
  const stage = { value: 1 };
  const strength = { value: 1 };
  const fields = { temperature: createFieldTexture('temperature'), moisture: createFieldTexture('moisture'), temperatureSeparated: createFieldTexture('temperatureSeparated') };
  const readyAppearances = Object.keys(APPEARANCES);
  const loaded = await Promise.all(readyAppearances.map(loadRootAppearance));
  const models = Object.fromEntries(readyAppearances.map((name, index) => [name,
    makeAppearanceModels(loaded[index], strength, stage, fields),
  ]));
  const maxAnisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
  for (const model of Object.values(models)) model.textures.forEach((texture) => { texture.anisotropy = maxAnisotropy; });
  scene.add(new THREE.AmbientLight('#f7f4eb', 0.8));
  const softbox = new THREE.RectAreaLight('#fff4de', 4.2, 13, 9);
  softbox.position.copy(LIGHT_POSITIONS.softbox);
  softbox.lookAt(0, 0, 0);
  scene.add(softbox);
  const key = new THREE.DirectionalLight('#fff5e2', 0.8);
  key.position.set(-8, 12, 6);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.bias = -0.00004;
  key.shadow.normalBias = 0.003;
  key.shadow.radius = 4;
  scene.add(key, key.target);
  const fill = new THREE.DirectionalLight('#e6efff', 0.55);
  fill.position.set(-2, 3, 12);
  scene.add(fill);
  const rim = new THREE.DirectionalLight('#fff3dd', 1.15);
  rim.position.copy(LIGHT_POSITIONS.rim);
  scene.add(rim);
  const shadow = makeGroundShadow();
  scene.add(shadow);
  let active = null;
  let disposed = false;

  return {
    availableAppearances: readyAppearances.slice(),
    render(kind = 'whole', options = {}) {
      if (disposed) throw new Error('The herb renderer has been disposed.');
      const appearance = options.appearance ?? 'fibrous';
      if (!APPEARANCES[appearance]) throw new Error(`Unknown herb appearance: ${appearance}`);
      const groups = models[appearance].groups;
      if (!groups[kind]) throw new Error(`Unknown herb render kind: ${kind}`);
      const isCross = kind === 'cross' || kind === 'crossSeparated';
      const defaults = DEFAULT_SIZE[kind];
      const width = Math.max(64, Math.round(Number(options.width) || defaults[0]));
      const height = Math.max(64, Math.round(Number(options.height) || defaults[1]));
      const angle = THREE.MathUtils.clamp(Number(options.angle) || 0, -15, 15);
      strength.value = THREE.MathUtils.clamp(Number.isFinite(options.textureStrength) ? options.textureStrength : 1, 0, 1.8);
      stage.value = { initial: 0, warming: 1, drying: 2 }[options.stage ?? 'warming'] ?? 1;
      if (active) scene.remove(active);
      active = groups[kind];
      scene.add(active);
      shadow.visible = !isCross;
      if (shadow.visible) fitGroundShadow(scene, active, shadow, key);
      const direction = isCross ? new THREE.Vector3(0, 0, 1) : kind === 'cutaway' ? FIELD_VIEW : VIEW;
      active.traverse((object) => {
        if (object.material?.userData.baseBumpScale !== undefined) {
          object.material.bumpScale = object.material.userData.baseBumpScale * strength.value;
        }
        if (object.material?.uniforms?.uViewDirection) {
          object.material.uniforms.uViewDirection.value.copy(direction);
        }
      });
      camera.position.copy(direction).multiplyScalar(35);
      camera.up.set(0, 1, 0);
      if (!isCross) camera.up.applyAxisAngle(direction, -angle * Math.PI / 180);
      camera.lookAt(0, 0, 0);
      const contentBounds = frameObject(camera, active, width, height, isCross ? 0.925 : kind === 'cutaway' ? 0.90 : 0.88);
      // Render extra transparent margins for the penumbra without resizing the object.
      const padding = isCross ? 0 : Math.ceil(Math.min(width, height) * 0.12);
      const padX = (camera.right - camera.left) / width * padding;
      const padY = (camera.top - camera.bottom) / height * padding;
      camera.left -= padX;
      camera.right += padX;
      camera.top += padY;
      camera.bottom -= padY;
      camera.updateProjectionMatrix();
      const canvasWidth = width + padding * 2, canvasHeight = height + padding * 2;
      renderer.setSize(canvasWidth, canvasHeight, false);
      renderer.render(scene, camera);
      const anchors = {};
      for (const [name, point] of Object.entries(active.userData.anchors)) {
        const p = point.clone().applyMatrix4(active.matrixWorld).project(camera);
        anchors[name] = [(p.x + 1) * canvasWidth / 2 - padding, (1 - p.y) * canvasHeight / 2 - padding];
      }
      if (kind === 'whole') {
        const axis = new THREE.Vector2(
          anchors.backCenter[0] - anchors.frontCenter[0],
          anchors.backCenter[1] - anchors.frontCenter[1],
        ).normalize();
        const normal = new THREE.Vector2(-axis.y, axis.x);
        if (normal.y > 0) normal.negate();
        const { mesh, backStart } = active.userData.lengthRings;
        const position = mesh.geometry.attributes.position;
        const vertex = new THREE.Vector3();
        const projectVertex = (index) => {
          vertex.fromBufferAttribute(position, index).applyMatrix4(mesh.matrixWorld).project(camera);
          return [(vertex.x + 1) * canvasWidth / 2 - padding, (1 - vertex.y) * canvasHeight / 2 - padding];
        };
        let farthest = -Infinity;
        let upperIndex = 0;
        for (let j = 0; j < RADIAL_SEGMENTS; j++) {
          const front = projectVertex(j), back = projectVertex(backStart + j);
          const score = (front[0] + back[0] - anchors.frontCenter[0] - anchors.backCenter[0]) * normal.x
            + (front[1] + back[1] - anchors.frontCenter[1] - anchors.backCenter[1]) * normal.y;
          if (score > farthest) {
            farthest = score;
            upperIndex = j;
            anchors.lengthStart = front;
            anchors.lengthEnd = back;
          }
        }
        anchors.detailTop = anchors.lengthEnd;
        anchors.detailBottom = projectVertex(backStart + (upperIndex + RADIAL_SEGMENTS / 2) % RADIAL_SEGMENTS);
      }
      if (kind === 'cutaway') {
        const project = (point) => {
          const p = point.clone().applyMatrix4(active.matrixWorld).project(camera);
          return [(p.x + 1) * canvasWidth / 2 - padding, (1 - p.y) * canvasHeight / 2 - padding];
        };
        anchors.heatArrows = active.userData.surfaceFlows.heat.map((pair) => pair.map(project));
        anchors.waterArrows = active.userData.surfaceFlows.water.map((pair) => pair.map(project));
      }
      return { url: renderer.domElement.toDataURL('image/png'), anchors, contentBounds, width, height, padding };
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      const geometries = new Set(), materials = new Set();
      for (const root of [...Object.values(models).flatMap((model) => Object.values(model.groups)), shadow]) {
        root.traverse((object) => {
          if (object.geometry) geometries.add(object.geometry);
          if (object.material) materials.add(object.material);
          if (object.customDepthMaterial) materials.add(object.customDepthMaterial);
        });
      }
      geometries.forEach((geometry) => geometry.dispose());
      materials.forEach((material) => material.dispose());
      Object.values(models).forEach((model) => model.textures.forEach((texture) => texture.dispose()));
      Object.values(fields).forEach((texture) => texture.dispose());
      key.shadow.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
    },
  };
}
