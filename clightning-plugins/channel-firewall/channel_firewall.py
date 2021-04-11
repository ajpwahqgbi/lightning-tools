#!/usr/bin/env python3
from pyln.client import Plugin

plugin = Plugin()
plugin.allowed_node_ids = {}

@plugin.hook("openchannel")
def openchannel(plugin: Plugin, openchannel: dict, **kwargs):
    peer_id = None
    try:
        peer_id = openchannel["id"]
    except KeyError:
        pass
    if peer_id is not None and peer_id in plugin.allowed_node_ids:
        return {"result": "continue"}
    else:
        return {"result": "reject", "error_message": "Please contact the operator to get permission to open a channel."}

@plugin.hook("openchannel2")
def openchannel2(plugin: Plugin, openchannel2: dict, **kwargs):
    peer_id = None
    try:
        peer_id = openchannel2["id"]
    except KeyError:
        pass
    if peer_id is not None and peer_id in plugin.allowed_node_ids:
        return {"result": "continue"}
    else:
        return {"result": "reject", "error_message": "Please contact the operator to get permission to open a channel."}

@plugin.init()
def init(options: dict, configuration: dict, plugin: Plugin, **kwargs):
    plugin.log(f"Plugin channel-firewall initialized with whitelisted nodes: {plugin.allowed_node_ids}.")

plugin.run()
