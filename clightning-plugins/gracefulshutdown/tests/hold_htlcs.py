#!/usr/bin/env python3
"""Plugin that holds on to HTLCs for 10 seconds.

Used to test restarts / crashes while HTLCs were accepted, but not yet
settled/forwarded

"""
from pyln.client import Plugin
import time

plugin = Plugin()


@plugin.hook('htlc_accepted', before=['gracefulshutdown.py'])
def on_htlc_accepted(htlc, plugin, **kwargs):
    plugin.log("Holding onto an incoming htlc")

    time.sleep(10)
    return {'result': 'continue'}


plugin.run()
