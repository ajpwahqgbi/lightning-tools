#!/usr/bin/env python3
from pyln.client import Plugin
from functools import reduce
import time
import secrets

plugin = Plugin()

@plugin.method("inflight_htlcs")
def inflight_htlcs(plugin: Plugin, **kwargs):
    peers = plugin.rpc.listpeers()["peers"]
    htlc_count = dict()
    total_num_htlcs = 0
    for peer in peers:
        if len(peer["channels"]) > 0:
            chan = peer["channels"][0]
            scid = chan["short_channel_id"]
            num_htlcs = len(chan["htlcs"])
            total_num_htlcs += num_htlcs
            if num_htlcs > 0:
                htlc_count[scid] = num_htlcs
    msg = f"Total {total_num_htlcs} in-flight HTLCs"
    if total_num_htlcs > 0:
        msg += " -- "
        msg += reduce(lambda x,y: x+"; "+y, [f"channel {scid} has {c}" for (scid, c) in htlc_count], "")
    msg += "."
    return {"message": msg}

@plugin.init()
def init(options: dict, configuration: dict, plugin: Plugin, **kwargs):
    plugin.log(f"Plugin inflighthtlcs initialized")

plugin.run()
