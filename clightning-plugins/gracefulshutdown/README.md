Graceful shutdown
----
This plugin adds a `shutdown_clean` command that rejects new incoming HTLCs, waits for in-flight HTLCs to resolve, and then shuts down lightningd.

To run tests in `tests/`, you need to install packages in `requirements-dev.txt`

and then run `pytest tests/`
