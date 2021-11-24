#!/usr/bin/env python3
from pyln.client import Plugin
import time
import os

plugin = Plugin()

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


@plugin.method("shutdown_clean")
def on_shutdown_clean(plugin, **kwargs):
    """
    Inject custom shutdown behaviour and then calls RPC `stop`
    """
    source_dir = os.path.dirname(__file__)
    chld_path = os.path.join(source_dir, 'gracefulshutdown.py')

    # will not return before child_plugin is running and initialized
    plugin.rpc.plugin_start(chld_path)

    num_inflight_htlcs = 1
    while num_inflight_htlcs > 0:
        num_inflight_htlcs = count_inflight_htlcs()
        if num_inflight_htlcs > 0:
            plugin.log(f"Waiting for {num_inflight_htlcs} HTLCs to resolve...")
            time.sleep(3)

    plugin.rpc.stop()


plugin.run()
