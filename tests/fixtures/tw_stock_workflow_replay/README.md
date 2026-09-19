# Readonly replay window fixture

This fixture minimizes the checked-in D7 readonly replay window index and its Model A D6 artifact. It preserves the formal path, identity, safety, checksum, and narrow validation-report shapes. The D6 manifest intentionally has no `run_id` or `status`, and preserves the three known full-contract gaps: no `not_copied_from_legacy_replay`, no `model_training_windows_traceable`, and no source OrderIntent list.

The fixture is for observation and parity tests only. It is not evidence that the complete `ReplayResultArtifact` validator passes.
