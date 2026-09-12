import { createHerbRenderer } from '../../原理图/src/render.js';
import { wrap } from './svg.js';
import { mechanism,workflow,boundaries,volumes,mapping } from './diagrams.js';
import * as plots from './quantitative.js';
import data from './data.json';

let rendererPromise;
const cache=new Map();
const functions=[null,null,workflow,null,volumes,mapping,
  plots.environment,plots.radius,plots.scales,plots.q1,plots.q2,plots.consistency,
  plots.drying,plots.finalProfiles,plots.movingField,plots.coupling,plots.comparison];

export async function renderFigure(id,options={}) {
  const n=Number(id);
  if(!Number.isInteger(n)||n<1||n>16)throw new Error('图像编号必须在 01–16 之间');
  if(!cache.has(n)){
    let body;
    if(n===1||n===3){
      rendererPromise??=createHerbRenderer();
      body=(n===1?mechanism:boundaries)(await rendererPromise);
    }else body=functions[n](data);
    cache.set(n,body);
  }
  return wrap(cache.get(n),options);
}
export const sourceInfo = {
  hashes:data.sources, checks:data.consistency,
  endHours:[data.q[3].endH,data.q[4].endH], endR:data.q[4].endR,
};
