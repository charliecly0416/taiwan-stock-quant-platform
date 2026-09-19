# Readonly workflow fixture

This fixture is a minimized copy of the production `tw.research_data_history.index.v1` and Model A manifest shapes. Paths and identifiers preserve the formal contract; market rows, provider payloads, timestamps unrelated to identity, and machine-specific paths are omitted. The two manifest SHA256 values in `repo/history/index.json` are hashes of the committed manifest files.

The fixture contains no credentials and no writable latest/provider pointer. It exists so the workflow CLI and resolver can be tested in a fresh checkout without reading ignored live data.
