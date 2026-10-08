// Astra DOM-shape regression probe, NOT real browser execution.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../../..');
const ai = process.argv.indexOf('--pack-dir');
const dir = ai >= 0 ? path.resolve(process.argv[ai + 1]) : path.join(root, 'step2_code/backend/.cache/human-review/T036-v2');
const source = fs.readFileSync(path.join(root, 'step2_code/backend/scripts/check-review-pack.cjs'), 'utf8');
const prefix = source.split('vm.runInNewContext(scriptMatch[1], context);')[0]
  .replace(/const outDir = [^;]+;/, 'const outDir = ' + JSON.stringify(dir) + ';');
const suffix = `
const originalQuery = Element.prototype.querySelectorAll;
Element.prototype.querySelectorAll = function(selector){
  const array = originalQuery.call(this, selector);
  if(selector !== '.op-sel') return array;
  // querySelectorAll returns a NodeList: indexed, iterable, with forEach/item,
  // but NOT an Array and has no Array.prototype.some method.
  const list = {length: array.length, item: i => array[i] || null,
    forEach: cb => array.forEach((e, i) => cb(e, i, list)),
    [Symbol.iterator]: function*(){ yield* array; }};
  array.forEach((e, i) => { list[i] = e; });
  return list;
};
vm.runInNewContext(scriptMatch[1], context);
const row = byId('questions-pane').children[0].querySelectorAll('.opinion-row')[0];
const sel = row.querySelectorAll('select')[0];
sel.value = '需修订';
(sel.listeners.change || []).forEach(fn => fn({}));
byId('filter-op').value = '需修订';
(byId('filter-op').listeners.change || []).forEach(fn => fn({}));
const visible = byId('questions-pane').children.filter(c => !c.className.split(/\\s+/).includes('hidden')).map(c => c.getAttribute('data-search').split(' ')[0]);
if(visible.length !== 1 || visible[0] !== 'q01') throw new Error('Wrong matches: ' + visible.join(','));
return visible;
`;
let result;
try {
  const visible = new Function('require', '__dirname', prefix + suffix)(require, path.join(root, 'step2_code/backend/scripts'));
  result = {layer: 'NodeList-shaped DOM stub, not browser', pack_dir: dir, pass: true, actual_visible: visible};
} catch (error) {
  result = {layer: 'NodeList-shaped DOM stub, not browser', pack_dir: dir, pass: false, error: error.message};
}
fs.writeFileSync(path.join(root, 'docs/collaboration/reviews/T036-nodelist-probe.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(result));
process.exitCode = result.pass ? 0 : 1;
