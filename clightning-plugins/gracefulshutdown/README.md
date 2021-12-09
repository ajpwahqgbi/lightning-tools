Graceful shutdown
----
This plugin adds a `shutdown` command that rejects new incoming HTLCs, waits for in-flight HTLCs to resolve, and then shuts down lightningd.

WARNING: This does not yet work as expected. Please do not rely on the stated behavior until this warning is removed.
