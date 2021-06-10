#!/usr/bin/python3
import sys
import json
from datetime import date, datetime
from pyln.client import LightningRpc
from os.path import expanduser
from mpmath import *

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

#Calculate the average shortest path length from root_node to each node in lowfee_nodes
def calculate_asp(edges, nodes):
    min_distance = dict()
    mega_adjacent = dict()
    processed = set()

    for (src, dest) in edges:
        if src not in mega_adjacent:
            mega_adjacent[src] = set()
        if dest not in mega_adjacent:
            mega_adjacent[dest] = set()
        mega_adjacent[src].add(dest)
        mega_adjacent[dest].add(src)
        min_distance[src] = sys.maxsize
        min_distance[dest] = sys.maxsize

    #Calculate shortest path lengths:
    bfs_queue = [(root_node, 0)]
    processed.add(root_node)
    while len(bfs_queue) > 0:
        (cur_node, distance) = bfs_queue.pop(0)
        for a in mega_adjacent[cur_node]:
            if (distance + 1) < min_distance[a]:
                min_distance[a] = distance + 1
            if a not in processed:
                bfs_queue.append((a, distance + 1))
                processed.add(a)

    #Calculate average shortest path lengths:
    #path_length_sum = reduce(lambda x,y: x+y, map(lambda n: min_distance[n], filter(lambda n: True if n in min_distance else False, nodes)))
    #return float(path_length_sum)/len(nodes)
    filter_func = lambda n: True if n in min_distance else False
    path_length_prod = reduce(lambda x,y: x*y, map(lambda n: mpf(min_distance[n]), filter(filter_func, nodes)))
    path_length_count = reduce(lambda x,y: x+y, map(lambda n: 1, filter(filter_func, nodes)))
    return power(path_length_prod, mpf(1.0) / mpf(path_length_count))

#####################################################
#MAIN BODY
#####################################################

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

mega_edges = set()
for n in megahub_nodes:
    for a in filter(lambda x: x in megahub_nodes, adjacent[n]):
        mega_edges.add((n, a))

asp = calculate_asp(mega_edges, megahub_nodes)
print("average shortest path in the megahub is %s" % nstr(asp, 6))
