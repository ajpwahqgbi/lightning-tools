Graceful shutdown
----
This plugin adds a `shutdown` command that rejects new incoming HTLCs, waits for in-flight HTLCs to resolve, and then shuts down lightningd.
