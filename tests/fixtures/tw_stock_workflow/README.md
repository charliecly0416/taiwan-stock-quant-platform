# Readonly workflow fixture

This fixture is a minimized copy of the production `tw.research_data_history.index.v1`, immutable day manifest, and Model A artifact shapes. Paths and identifiers preserve the formal contract; market rows, provider payloads, timestamps unrelated to identity, and machine-specific paths are omitted. Every file declared by each Model A slot in `repo/history/index.json` is bound by its committed size and SHA256, and the immutable day manifest binds the complete index day entry.

The fixture contains no credentials and no writable latest/provider pointer. It exists so the workflow CLI and resolver can be tested in a fresh checkout without reading ignored live data.
