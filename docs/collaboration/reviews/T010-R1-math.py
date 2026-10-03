"""Run using backend/.venv Python; no model download."""
import numpy as np
from campus_assistant.retrieval.dense import DenseIndex
from campus_assistant.retrieval.hybrid import rrf_fusion
a, b = {'chunk_id': 'a'}, {'chunk_id': 'b'}
def hit(c, r):
    return {'chunk': c, 'rank': r, 'score': 9.0}
r = rrf_fusion([hit(a, 1), hit(b, 2)], [hit(b, 1)])
assert r[0]['chunk']['chunk_id'] == 'b'
assert abs(r[0]['score'] - (1/62 + 1/61)) < 1e-12
d = DenseIndex([a, b], np.array([[1, 0], [0, 1]], dtype=np.float32))
assert d.search(np.array([0, 1], dtype=np.float32))[0]['chunk']['chunk_id'] == 'b'
print('dense + RRF hand calculation OK')
