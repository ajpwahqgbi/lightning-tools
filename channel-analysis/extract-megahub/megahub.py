#!/usr/bin/python3
import sys
import json
from datetime import date, datetime
from pyln.client import LightningRpc
from os.path import expanduser

rpc = LightningRpc(expanduser("~") + "/.lightning/bitcoin/lightning-rpc")
N = 1 # min number of triangles
megahub_nodes = set()
adjacent = dict() # node_id -> adjacent node_ids (i.e. other node_ids to which this node has a direct channel)
min_chan_size = 100000 #satoshis minimum in a channel for it to be considered

def print_usage_and_die():
    sys.stderr.write("Usage:\n")
    sys.stderr.write("%s N node_id [node_id ...]" % sys.argv[0])
    sys.stderr.write("\n")
    sys.stderr.write("Extracts the megahub rooted at the specified node_ids with all nodes having at least N\n")
    sys.stderr.write("triangles where both other nodes are already in the megahub.\n")
    sys.stderr.write("\n")
    sys.exit(1)

# parse command line args:
if len(sys.argv) < 3:
    print_usage_and_die()

N = int(sys.argv[1])
for i in range(2, len(sys.argv)): 
    node_id = sys.argv[i]
    megahub_nodes.add(node_id)

# build adjacent dict:
for chan in rpc.listchannels()["channels"]:
    src = chan["source"]
    dst = chan["destination"]

    if src not in adjacent:
        adjacent[src] = set()
    if dst not in adjacent:
        adjacent[dst] = set()

    if chan["active"] and int(chan["satoshis"]) > min_chan_size:
        adjacent[src].add(dst)

# extract megahub:
finished = False
while not finished:
    potentials = set()
    finished = True
    for node in megahub_nodes:
        for n in filter(lambda x: x not in megahub_nodes, adjacent[node]):
            potentials.add(n)
    for src in potentials:
        triangle_edges = set()
        for dst1 in filter(lambda x: x in megahub_nodes, adjacent[src]):
            # if there exists another adjacency dst2 that is in turn directly
            # connected to dst1, the edges (src, dst1) and (src, dst2) are
            # triangle edges
            if (src, dst1) not in triangle_edges:
                for dst2 in filter(lambda x: x in megahub_nodes and x != dst1, adjacent[src]):
#                for dst2 in filter(lambda x: x != dst1, adjacent[src]): #FIXME do triangles have to have *both* other nodes already in the megahub?
                    if dst1 in adjacent[dst2]:
                        triangle_edges.add((src, dst1))
                        triangle_edges.add((src, dst2))
                        break
        if len(triangle_edges) - 1 >= N:
            megahub_nodes.add(src)
            finished = False

print("%d nodes in the megahub:" % len(megahub_nodes))
print(megahub_nodes)
