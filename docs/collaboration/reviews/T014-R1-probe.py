"""Local-only acceptance probes; no real provider or external request."""
import importlib.util
import json
import shutil
import tempfile
from pathlib import Path

root = Path.cwd()
spec = importlib.util.spec_from_file_location('smoke', root / 'scripts/live-smoke-deepseek.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)

class LocalFake:
    provider_id = 'local-fake-only'
    _base_url = 'http://127.0.0.1:1'
    model = 'local-test-model'
    max_tokens = 7
    calls = 0
    def generate(self, **kwargs):
        self.calls += 1
        return {'type': 'insufficient_evidence', 'reason': 'local fake'}

no_provider = smoke.run_smoke(live=True, corpus=root/'examples/parse-corpus', answer_preview_chars=100, provider_factory=lambda: None)
bad_corpus = smoke.run_smoke(live=False, corpus=root/'.cache/no-such-t014-corpus', answer_preview_chars=100)
base = Path(tempfile.mkdtemp(prefix='astra-t014-', dir=root/'.cache'))
corpus = base/'corpus'
shutil.copytree(root/'examples/parse-corpus', corpus)
manifest_path = corpus/'manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
for doc in manifest['documents']:
    doc['is_synthetic'] = False
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
fake = LocalFake()
r = smoke.run_smoke(live=True, corpus=corpus, answer_preview_chars=100, provider_factory=lambda: fake)
print(json.dumps({
    'external_network_calls': 0,
    'missing_provider_exit_ok': no_provider['exit_ok'],
    'invalid_corpus_dryrun_exit_ok': bad_corpus['exit_ok'],
    'non_synthetic_fake_generate_calls': fake.calls,
    'reported_target': r['target'],
    'injected_target': fake._base_url,
    'reported_model': r['model_planned'],
    'injected_model': fake.model,
}, ensure_ascii=True, indent=2))
