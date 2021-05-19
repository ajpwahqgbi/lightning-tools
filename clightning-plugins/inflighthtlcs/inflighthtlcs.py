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
    chan_htlcs = dict()
    onchain_htlc_count = dict()
    onchain_chan_htlcs = dict()
    total_num_htlcs = 0
    for peer in peers:
        if len(peer["channels"]) > 0:
            chan = peer["channels"][0]
            scid = chan["short_channel_id"]
            num_htlcs = len(chan["htlcs"])
            total_num_htlcs += num_htlcs
            if num_htlcs > 0 and chan["state"] == "CHANNELD_NORMAL":
                htlc_count[scid] = num_htlcs
                chan_htlcs[scid] = chan["htlcs"]
            elif num_htlcs > 0 and chan["state"] == "ONCHAIN":
                onchain_htlc_count[scid] = num_htlcs
                onchain_chan_htlcs[scid] = chan["htlcs"]
    return {"num_inflight": total_num_htlcs, "channel_inflight_count": htlc_count, "channel_htlcs": chan_htlcs, "resolving_onchain": onchain_htlc_count, "onchain_htlcs": onchain_chan_htlcs}

@plugin.init()
def init(options: dict, configuration: dict, plugin: Plugin, **kwargs):
    plugin.log(f"Plugin inflighthtlcs initialized")

plugin.run()
