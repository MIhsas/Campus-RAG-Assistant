"""Allow running as: python -m campus_assistant.corpus"""

from __future__ import annotations

import sys

from campus_assistant.corpus.validate import main

sys.exit(main())
