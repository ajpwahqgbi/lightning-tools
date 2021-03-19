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
    my_node_id = plugin.rpc.getinfo().get('id')
    nodes = plugin.rpc.listnodes()['nodes']
    alias_objs = []
    for node in nodes:
        s = node['alias'] if len(node) != 0 and 'alias' in node else node['nodeid'][0:7]
        obj = {
            "id": node['nodeid'],
            "alias": s
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
