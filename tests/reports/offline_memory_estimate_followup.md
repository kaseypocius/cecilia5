# Conservative-estimate admission correction

The reported 14.6 GiB estimate / 11.2 GiB budget error was a preflight rejection, not a measured allocation failure. Estimates include decoded-table precision and copy headroom and can exceed actual native RSS.

On systems with resident-memory telemetry, estimates now choose concurrency. An estimate above budget requests one worker with the full existing RSS allowance; actual over-budget workers are still stopped and cleaned up. Auto mode uses a single pass when only one worker is allowed. Explicit acceleration/stem requirements retain their requested routing behavior. Systems without telemetry retain the early rejection.

Validation: a real StateVar2 worker rendered 19,200 stereo frames with a forced 14.6 GiB estimate and a 192 MiB RSS allowance. The native guard termination/restart test still passes, as do fallback rejection, destination preservation and single-pass scheduling tests. Full discovery: 135 passed, 66 skipped (201 total); all six engine scenarios pass. See `offline_memory_estimate_trial.log`, `offline_memory_unit.log` and `offline_memory_engine.log`.

The screenshot's exact input/module configuration has not been reproduced. This removes a conservative estimate as a hard blocker on monitored systems; a job whose actual resident memory exceeds the budget will still fail with a measured-memory error. No native rendering code changed, so the retained gigabyte-size measurements remain applicable.
