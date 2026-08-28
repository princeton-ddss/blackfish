"""Worked example pipelines.

Each one runs anywhere -- no GPU, no model download, no scheduler -- because
the expensive part is stubbed and everything around it is what real code does.
They are documentation that executes: each is covered by tests, so a change to
the core that breaks an idiom breaks a build.

- :mod:`~blackfish.pipelines.examples.word_count` -- the smallest pipeline that
  uses all three cardinalities.
- :mod:`~blackfish.pipelines.examples.embed` -- run a model over one large
  file: chunking, shards on disk, a manifest fold.
- :mod:`~blackfish.pipelines.examples.resumable` -- a standing run over a
  growing directory that survives a coordinator restart.
- :mod:`~blackfish.pipelines.examples.compare` -- fan out to two models of very
  different speeds and join their results per document.
- :mod:`~blackfish.pipelines.examples.transcribe` -- a multi-stage pipeline
  whose stages exchange artifacts on disk rather than payloads.
- :mod:`~blackfish.pipelines.examples.summarize` -- cheap IO-bound work on the
  login node feeding expensive GPU work in an allocation.
"""
