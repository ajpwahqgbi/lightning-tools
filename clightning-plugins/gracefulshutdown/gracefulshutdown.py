#!/usr/bin/env python3
from pyln.client import Plugin
import time
import secrets

plugin = Plugin()


@plugin.hook("htlc_accepted", after=['hold_htlcs.py'])
def htlc_accepted(plugin: Plugin, onion: dict, htlc: dict, **kwargs):
    return {"result": "fail", "failure_message": "2002"}


@plugin.init()
def init(options: dict, configuration: dict, plugin: Plugin, **kwargs):
    plugin.log(f"Plugin gracefulshutdown initialized")

plugin.run()
