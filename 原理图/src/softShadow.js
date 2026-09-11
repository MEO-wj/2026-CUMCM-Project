import { Matrix4, ShaderMaterial, Vector2 } from 'three';

// PCSS blocker search and contact-hardening filtering, following the Three.js
// r171 PCSS example and pmndrs/drei SoftShadows. Our directional shadow camera
// is orthographic, so normalized depth differences are converted to world units.
export function createSoftShadowMaterial() {
  return new ShaderMaterial({
    transparent: true,
    depthWrite: false,
    toneMapped: false,
    uniforms: {
      uDepthMap: { value: null },
      uShadowMatrix: { value: new Matrix4() },
      uMapSize: { value: new Vector2(2048, 2048) },
      uFrustum: { value: new Vector2(20, 20) },
      uDepthRange: { value: 20 },
      uSearchGap: { value: 3 },
      uAngularRadius: { value: 0.30 },
      uBias: { value: -0.00004 },
      uOpacity: { value: 0.34 },
    },
    vertexShader: `
      uniform mat4 uShadowMatrix;
      varying vec4 vShadow;
      void main() {
        vec4 world = modelMatrix * vec4(position, 1.0);
        vShadow = uShadowMatrix * world;
        gl_Position = projectionMatrix * viewMatrix * world;
      }
    `,
    fragmentShader: `
      #include <packing>
      uniform sampler2D uDepthMap;
      uniform vec2 uMapSize;
      uniform vec2 uFrustum;
      uniform float uDepthRange;
      uniform float uSearchGap;
      uniform float uAngularRadius;
      uniform float uBias;
      uniform float uOpacity;
      varying vec4 vShadow;

      vec2 diskSample(int index, int count, float angle) {
        float r = sqrt((float(index) + 0.5) / float(count));
        float theta = float(index) * 2.39996323 + angle;
        return vec2(cos(theta), sin(theta)) * r;
      }
      float depthAt(vec2 uv) {
        if (any(lessThan(uv, vec2(0.0))) || any(greaterThan(uv, vec2(1.0)))) return 1.0;
        return unpackRGBAToDepth(texture2D(uDepthMap, uv));
      }
      void main() {
        vec3 coord = vShadow.xyz / vShadow.w;
        if (any(lessThan(coord, vec3(0.0))) || any(greaterThan(coord, vec3(1.0)))) {
          gl_FragColor = vec4(0.0);
          return;
        }
        float receiver = coord.z + uBias;
        float angle = fract(sin(dot(floor(coord.xy * uMapSize), vec2(12.9898, 78.233))) * 43758.5453) * 6.28318530718;
        vec2 search = vec2(uAngularRadius * uSearchGap) / uFrustum;
        float sumDepth = 0.0;
        float blockers = 0.0;
        for (int i = 0; i < 32; i++) {
          float depth = depthAt(coord.xy + diskSample(i, 32, angle) * search);
          if (depth < receiver) { sumDepth += depth; blockers += 1.0; }
        }
        if (blockers < 0.5) {
          gl_FragColor = vec4(0.0);
          return;
        }
        float separation = max(0.0, receiver - sumDepth / blockers) * uDepthRange;
        float centerDepth = depthAt(coord.xy);
        if (centerDepth < receiver) {
          float localGap = max(0.0, receiver - centerDepth) * uDepthRange;
          separation = min(separation, localGap * 1.5 + 0.008);
        }
        vec2 radius = max(vec2(1.15) / uMapSize, vec2(uAngularRadius * separation) / uFrustum);
        float visibility = 0.0;
        for (int i = 0; i < 96; i++) {
          float depth = depthAt(coord.xy + diskSample(i, 96, angle + 1.57079632679) * radius);
          visibility += step(receiver, depth);
        }
        gl_FragColor = vec4(0.0, 0.0, 0.0, uOpacity * (1.0 - visibility / 96.0));
      }
    `,
  });
}
