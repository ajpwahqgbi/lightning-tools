#!/usr/bin/env python3
#Pipe input from node_recommender.py
import sys, json
import math
from functools import reduce

def trunc_pad(str_in, max_len):
    """Truncates str_in to max_len chars and pads with spaces to exactly max_len"""
    ret = str_in.strip()[0:max_len]
    if len(str_in.strip()) > max_len:
        for i in range(max_len - 3, max_len):
            ret = ret[0:i] + "." + ret[i+1:]
    for i in range(0, max_len - len(ret)):
        ret += " "
    return ret

def f(rank):
    return 1.0 + (math.log(1.0 + rank) / math.log(8))

n = 10 if len(sys.argv) == 1 else int(sys.argv[1])
json_data = json.load(sys.stdin)
cur_maxflow_geo = float(json_data["root_node_metrics"]["existing_maxflow_geomean"])
cur_shortest_geo = float(json_data["root_node_metrics"]["existing_shortest_path_geomean"])
cur_cheapest_geo = float(json_data["root_node_metrics"]["existing_cheapest_ppm_geomean"])
print("Found %d potential peers" % len(json_data["peer_metrics"]))
print("Current maxflow = %f" % cur_maxflow_geo)
print("Current shortest = %f" % cur_shortest_geo)
print("Current cheapest = %f" % cur_cheapest_geo)
print("")

peers = json_data["peer_metrics"]
peers_by_maxflow = sorted(peers, key = lambda x: float(x["new_maxflow_geomean"]), reverse = True)
peers_by_shortest = sorted(peers, key = lambda x: float(x["new_shortest_path_geomean"]))
peers_by_cheapest = sorted(peers, key = lambda x: float(x["new_cheapest_ppm_geomean"]))
peer_products = dict()

print("-----")
print("")
print("Top %d potential peers by maxflow:" % n)
print("")
for i in range(0, n):
    peer = peers_by_maxflow[i]
    print("%.4f - %s (%s)" % (float(peer["new_maxflow_geomean"]), trunc_pad(peer["peer_alias"], 30), peer["peer_id"]))
for i in range(0, len(peers_by_maxflow)):
    peer = peers_by_maxflow[i]
    peer_id = peer["peer_id"]
    peer_products[peer_id] = f(i)
print("")

print("-----")
print("")
print("Top %d potential peers by shortest paths:" % n)
print("")
for i in range(0, n):
    peer = peers_by_shortest[i]
    print("%.4f - %s (%s)" % (float(peer["new_shortest_path_geomean"]), trunc_pad(peer["peer_alias"], 30), peer["peer_id"]))
for i in range(0, len(peers_by_shortest)):
    peer = peers_by_shortest[i]
    peer_id = peer["peer_id"]
    peer_products[peer_id] = peer_products[peer_id] * f(i)
print("")

print("-----")
print("")
print("Top %d potential peers by cheapest ppm:" % n)
print("")
for i in range(0, n):
    peer = peers_by_cheapest[i]
    print("%.4f - %s (%s)" % (float(peer["new_cheapest_ppm_geomean"]), trunc_pad(peer["peer_alias"], 30), peer["peer_id"]))
for i in range(0, len(peers_by_cheapest)):
    peer = peers_by_cheapest[i]
    peer_id = peer["peer_id"]
    peer_products[peer_id] = peer_products[peer_id] * f(i)
print("")

print("-----")
print("")
print("Top %d potential peers by f(rank) product:" % n)
print("(where f() is some logarithmic function)")
print("")
peers_by_rank_product = sorted(peers, key = lambda x: peer_products[x["peer_id"]])
for i in range(0, n):
    peer = peers_by_rank_product[i]
    print("%7.4f - %s (%s)" % (peer_products[peer["peer_id"]], trunc_pad(peer["peer_alias"], 30), peer["peer_id"]))
print("")

print("-----")
