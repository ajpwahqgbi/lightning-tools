#!/usr/bin/env python3
from pyln.client import Plugin
from threading import Lock
import json

plugin = Plugin()

@plugin.method("listaliases")
def listaliases(plugin):
    """List aliases of known nodes on the Lightning Network.

    Returns pretty-printed JSON output for use in other scripts.
    """
    nodes = plugin.rpc.listnodes()['nodes']
    alias_objs = []
    for node in nodes:
        if len(node) != 0 and 'alias' in node:
            obj = {
                "id": node['nodeid'],
                "alias": node['alias']
            }
            alias_objs.append(obj)

    wrapper_obj = {
        "nodes": alias_objs
    }

    return wrapper_obj

@plugin.init()
def init(options, configuration, plugin):
    plugin.mutex = Lock()
    plugin.log(f"Plugin listaliases initialized")


plugin.run()
