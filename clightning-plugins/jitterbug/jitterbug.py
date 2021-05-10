#!/usr/bin/env python3
from pyln.client import Plugin
import time
import secrets

plugin = Plugin()
plugin.max_delay = secrets.randbelow(5) + secrets.randbelow(50) + secrets.randbelow(500) + secrets.randbelow(5000)

@plugin.hook("htlc_accepted")
def htlc_accepted(plugin: Plugin, onion: dict, htlc: dict, **kwargs):
    sleepytime = secrets.randbelow(plugin.max_delay)
    time.sleep(sleepytime / 1000.0)
    return {"result": "continue"}

@plugin.init()
def init(options: dict, configuration: dict, plugin: Plugin, **kwargs):
    plugin.log(f"Plugin jitterbug initialized with max_delay {plugin.max_delay}")

plugin.run()
