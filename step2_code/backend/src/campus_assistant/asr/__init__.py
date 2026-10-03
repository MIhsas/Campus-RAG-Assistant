"""Local speech recognition adapters (T020).

Local-only ASR on Windows CPU. The service loads models exclusively from
a configured local directory — it never performs automatic downloads and
never contacts cloud ASR or paid APIs. Audio and transcripts are processed
only within the request and always cleaned up.
"""
