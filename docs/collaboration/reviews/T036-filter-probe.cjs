// Astra independent causal probe. DOM stub, NOT real browser evidence.
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const root = path.resolve(__dirname, '../../..');
const supplied = fs.readFileSync(path.join(root, 'step2_code/backend/scripts/check-review-pack.cjs'), 'utf8');
const argIndex = process.argv.indexOf('--pack-dir');
const packDir = argIndex >= 0 ? path.resolve(process.argv[argIndex + 1]) : path.join(root, 'step2_code/backend/.cache/human-review/T036-v1');
const prefix = supplied.split('vm.runInNewContext(scriptMatch[1], context);')[0]
  .replace(/const outDir = [^;]+;/, 'const outDir = ' + JSON.stringify(packDir) + ';');
const patch = `
// DOM textContent includes own HTML text and descendant text, unlike original stub.
Object.defineProperty(Element.prototype, 'textContent', {
  get(){ return (this._text || '') + (this._innerHTML || '').replace(/<[^>]*>/g, '') + this.children.map(c => c.textContent || '').join(''); },
  set(v){ this._text = String(v); }
});
const oldQuery = Element.prototype.querySelectorAll;
Element.prototype.querySelectorAll = function(sel){
  const parts = sel.trim().split(/\\s+/);
  if(parts.length === 1) return oldQuery.call(this, sel);
  return oldQuery.call(this, parts[0]).flatMap(e => e.querySelectorAll(parts.slice(1).join(' ')));
};
vm.runInNewContext(scriptMatch[1], context);
const firstOpinion = byId('questions-pane').children[0].querySelectorAll('.opinion-row')[0].querySelectorAll('select')[0];
firstOpinion.value = '需修订';
(firstOpinion.listeners.change || []).forEach(fn => fn({}));
byId('filter-op').value = '需修订';
(byId('filter-op').listeners.change || []).forEach(fn => fn({}));
const cards = byId('questions-pane').children;
const visible = cards.filter(c => !c.className.split(/\\s+/).includes('hidden')).map(c => c.getAttribute('data-search').split(' ')[0]);
const result = { layer: 'DOM stub, not browser', changed: 'q/q01/f1-s1', expected_visible: ['q01'], actual_visible: visible, pass: visible.length === 1 && visible[0] === 'q01' };
fs.writeFileSync(path.join(root, 'docs/collaboration/reviews/T036-filter-probe.json'), JSON.stringify(result, null, 2) + '\\n');
console.log(JSON.stringify(result));
process.exitCode = result.pass ? 0 : 1;
`;
// Resolve original stub's pack path exactly as if it ran in backend/scripts.
new Function('require', '__dirname', 'process', 'root', prefix + patch)(require, path.join(root, 'step2_code/backend/scripts'), process, root);
