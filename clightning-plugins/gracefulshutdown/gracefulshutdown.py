#!/usr/bin/env python3
from pyln.client import Plugin
import time
import secrets

plugin = Plugin()
plugin.stop_incoming_htlcs = False

def count_inflight_htlcs():
    peers = plugin.rpc.listpeers()["peers"]
    total_num_htlcs = 0
    for peer in peers:
        if len(peer["channels"]) > 0:
            chan = peer["channels"][0]
            if chan["state"] == "CHANNELD_NORMAL":
                num_htlcs = len(chan["htlcs"])
                total_num_htlcs += num_htlcs
    return total_num_htlcs

@plugin.hook("htlc_accepted")
def htlc_accepted(plugin: Plugin, onion: dict, htlc: dict, **kwargs):
    if plugin.stop_incoming_htlcs == False:
        return {"result": "continue"}
    else:
        return {"result": "fail", "failure_message": "2002"}

@plugin.method("shutdown")
def shutdown(plugin: Plugin):
    plugin.stop_incoming_htlcs = True
    num_inflight_htlcs = 1
    while num_inflight_htlcs > 0:
        num_inflight_htlcs = count_inflight_htlcs()
        if num_inflight_htlcs > 0:
            plugin.log(f"Waiting for {num_inflight_htlcs} HTLCs to resolve...")
            time.sleep(3)
    plugin.rpc.stop()

@plugin.init()
def init(options: dict, configuration: dict, plugin: Plugin, **kwargs):
    plugin.log(f"Plugin gracefulshutdown initialized")

plugin.run()
