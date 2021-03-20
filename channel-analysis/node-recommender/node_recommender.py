#!/usr/bin/env python3
#Pipe input from `lightning-cli listchannels`
#pip3 install PyMaxflow mpmath
import sys, signal, json
from functools import reduce
import maxflow
from mpmath import *
from enum import Enum


#####################################################
#GLOBAL VARIABLES
#####################################################

root_node = 0
root_node_id = "" 

#Define the "low fee" threshold for the *total path*
base_fee_threshold = 0
permillion_fee_threshold = 0

#Define the minimum channels and capacity requirements to consider a node for an outgoing channel
min_channels = 10
min_capacity = 15000000 #NOT about total capacity of a channel path

nodes = set()
node_to_id = dict()
id_to_node = dict()
node_to_alias = dict()
chan_fees = {}
chan_capacity = {}
outgoing = {}
incoming = {}
new_peer_benefit = {}

class LNSoftwareType(Enum):
    LND = "LND"
    CLI = "C-Lightning"
    UKN = 3

ln_software_type = LNSoftwareType.UKN


#####################################################
#FUNCTION DEFINITIONS
#####################################################

def print_usage_and_die():
    sys.stderr.write("Usage:\n")
    sys.stderr.write("with C-Lightning: (echo \"{\"; lightning-cli listnodes | tail -n +2 | head -n -2; echo \"],\"; lightning-cli listchannels | tail -n +2) | %s root_node base_fee permillion_fee [min_channels] [min_capacity]\n" % sys.argv[0])
    sys.stderr.write("with LND: lncli describegraph | %s root_node base_fee permillion_fee [min_channels] [min_capacity]\n" % sys.argv[0])
    sys.stderr.write("\n")
    sys.stderr.write("root_node: Your node pubkey\n")
    sys.stderr.write("base_fee: The maximum base fee (in milisatoshi) accumulated along a route to remain \"low-fee reachable\"\n")
    sys.stderr.write("permillion_fee: The maximum permillion fee accumulated along a route to remain \"low-fee reachable\"\n")
    sys.stderr.write("min_channels: The minimum number of channels a node must have to consider peering with it (optional, default %d)\n" % min_channels)
    sys.stderr.write("min_capacity: The minimum total capacity a node (in satoshi) must have to consider peering with it.  Unrelated to the capacity of channels along a route. (optional, default %d)\n" % min_capacity)
    sys.exit(1)

def sigint_handler(signal, frame):
    print('\nInterrupted')
    sys.exit(0)

def detect_ln_software_type(json_data):
    try:
        buf = json_data['channels'][0]
        return LNSoftwareType.CLI
    except KeyError:
        pass
    try:
        buf = json_data['edges'][0]
        return LNSoftwareType.LND
    except KeyError:
        return LNSoftwareType.UKN

def parse_node_aliases(json_data):
    for node in json_data['nodes']:
        if 'alias' in node and node['nodeid'] in id_to_node:
            n = id_to_node[node['nodeid']]
            node_to_alias[n] = node['alias']

def node_is_big_enough(n):
    num_channels = 0
    total_capacity = 0
    if n in outgoing:
        num_channels += len(outgoing[n])
        total_capacity += reduce(lambda x,y: x+y, [chan_capacity[(n, o)] for o in outgoing[n]])
    if n in incoming:
        num_channels += len(incoming[n])
        total_capacity += reduce(lambda x,y: x+y, [chan_capacity[(i, n)] for i in incoming[n]])

    if num_channels < min_channels or total_capacity < min_capacity:
        return False
    else:
        return True

def print_top_new_peers(num):
    cnt = 0
    for (n, b) in sorted(new_peer_benefit.items(), key = lambda x: x[1], reverse = True):
        if n in incoming[root_node] or n in outgoing[root_node]:
            continue
        if not node_is_big_enough(n):
            continue

        peer_name = (node_to_alias[n] + " (%s)" % node_to_id[n][0:7]) if n in node_to_alias else node_to_id[n] 
        print("%f benefit from peering with node %s" % (b, peer_name))
        cnt += 1
        if cnt >= num:
            break

def get_unweighted_maxflow(source, sink, edges):
    node_map = dict()
    source_cap = 0
    sink_cap = 0

    i = 0
    for (src, dest) in edges:
        if src not in node_map:
            node_map[src] = i
            i += 1
        if dest not in node_map:
            node_map[dest] = i
            i += 1
        if src == source:
            source_cap += 1
        if dest == sink:
            sink_cap += 1
    g = maxflow.Graph[int](i, len(edges))
    g.add_nodes(i)

    for (src, dest) in edges:
        g_src = node_map[src]
        g_dest = node_map[dest]
        g.add_edge(g_src, g_dest, 1, 0)
    g.add_tedge(node_map[source], source_cap, 0)
    g.add_tedge(node_map[sink], 0, sink_cap)

    return g.maxflow()

#Returns a set of node tuples
#Note that not all routes through the low-fee reachable subgraph are low-fee routes!
def get_lowfee_reachable_subgraph(proposed_new_peer=None, max_hops=None):
    lowfee_edges = set()
    lowfee_nodes = set()
    min_cost_to_node = dict() #maps to a set of fee tuples (permillion, base) of costs to reach that node
                              #that lie along the Pareto frontier (i.e, there is no other min_cost_to_node
                              #that is strictly worse on both permillion and base)
    processed_nodes = set()
    queued = set()
    if max_hops == None:
        max_hops = 20

    min_cost_to_node[root_node] = set()
    min_cost_to_node[root_node].add((0, 0)) #(feerate_min_permillion, feerate_min_base)
    processed_nodes.add(root_node)
    queued.add(root_node)
    bfs_queue = [(n, 1) for n in outgoing[root_node]]
    for o in outgoing[root_node]:
        min_cost_to_node[o] = set()
        min_cost_to_node[o].add((0, 0))
        lowfee_edges.add((root_node, o))
        queued.add(o)

    if proposed_new_peer is not None:
        lowfee_edges.add((root_node, proposed_new_peer))
        min_cost_to_node[proposed_new_peer] = set()
        min_cost_to_node[proposed_new_peer].add((0, 0))
        queued.add(proposed_new_peer)
        bfs_queue.append((proposed_new_peer, 1))
    #use (0, 0) here instead of chan_fees[(root_node, n)] because we control these fees and they're independent of the peer node's low-fee reachability

    while len(bfs_queue) > 0:
        (cur_node, cur_hops) = bfs_queue.pop(0)
        processed_nodes.add(cur_node)
        min_feerates = min_cost_to_node[cur_node]
        for min_feerate in min_feerates:
            (permillion_fee, base_fee) = min_feerate

            if permillion_fee > permillion_fee_threshold or base_fee > base_fee_threshold:
                continue

            if cur_node not in outgoing:
                continue

            for o in outgoing[cur_node]:
                (new_permillion_fee, new_base_fee) = chan_fees[(cur_node, o)]
                new_permillion_fee += permillion_fee
                new_base_fee += base_fee

                if new_permillion_fee <= permillion_fee_threshold and new_base_fee <= base_fee_threshold:
                    lowfee_edges.add((cur_node, o))
                    if o not in processed_nodes and o not in queued and cur_hops < max_hops:
                        queued.add(o)
                        bfs_queue.append((o, cur_hops + 1))
                    is_pareto_dominated = False
                    if o not in min_cost_to_node:
                        min_cost_to_node[o] = set()
                    for c in min_cost_to_node[o]:
                        if c[0] < new_permillion_fee and c[1] < new_base_fee:
                            is_pareto_dominated = True
                            break
                    if not is_pareto_dominated:
                        min_cost_to_node[o].add((new_permillion_fee, new_base_fee))

    for (src, dest) in lowfee_edges:
      lowfee_nodes.add(src)
      lowfee_nodes.add(dest)

    return (lowfee_edges, lowfee_nodes, min_cost_to_node)

def get_lowfee_reachable_unweighted_maxflows(lowfee_edges, lowfee_nodes):
    lowfee_maxflows = dict()
    for cur_node in lowfee_nodes:
        #calculate the maxflow from root_node -> cur_node with all channels having unit weight
        lowfee_maxflows[cur_node] = get_unweighted_maxflow(root_node, cur_node, lowfee_edges)
    return lowfee_maxflows

def get_lowfee_reachable_ppm_geomean(lowfee_nodes, min_cost_to_node):
    cheapest_route = dict()

    for cur_node in lowfee_nodes:
        min_costs = min_cost_to_node[cur_node]
        mincost = sorted(min_costs, key = lambda x: x[0])[0]
        cheapest_route[cur_node] = mincost[0]

    #ppm_sum = reduce(lambda x,y: x+y, [ppm for n, ppm in cheapest_route.items()])
    ppm_prod = reduce(lambda x,y: x*y, [ppm if ppm != 0 else 1 for n, ppm in cheapest_route.items()])
    #ppm_mean = float(ppm_sum) / float(len(cheapest_route))
    ppm_geomean = power(ppm_prod, mpf(1.0) / mpf(len(cheapest_route)))

    return ppm_geomean

#Calculate the average shortest path length from root_node to each node in lowfee_nodes
def calculate_asp(edges, lowfee_nodes):
    min_distance = dict()
    lowfee_adjacent = dict()
    processed = set()

    for (src, dest) in edges:
        if src not in lowfee_adjacent:
            lowfee_adjacent[src] = set()
        if dest not in lowfee_adjacent:
            lowfee_adjacent[dest] = set()
        lowfee_adjacent[src].add(dest)
        lowfee_adjacent[dest].add(src)
        min_distance[src] = sys.maxsize
        min_distance[dest] = sys.maxsize

    #Calculate shortest path lengths:
    bfs_queue = [(root_node, 0)]
    processed.add(root_node)
    while len(bfs_queue) > 0:
        (cur_node, distance) = bfs_queue.pop(0)
        for a in lowfee_adjacent[cur_node]:
            if (distance + 1) < min_distance[a]:
                min_distance[a] = distance + 1
            if a not in processed:
                bfs_queue.append((a, distance + 1))
                processed.add(a)

    #Calculate average shortest path lengths:
    #path_length_sum = reduce(lambda x,y: x+y, map(lambda n: min_distance[n], filter(lambda n: True if n in min_distance else False, lowfee_nodes)))
    #return float(path_length_sum)/len(lowfee_nodes)
    filter_func = lambda n: True if n in min_distance else False
    path_length_prod = reduce(lambda x,y: x*y, map(lambda n: mpf(min_distance[n]), filter(filter_func, lowfee_nodes)))
    path_length_count = reduce(lambda x,y: x+y, map(lambda n: 1, filter(filter_func, lowfee_nodes)))
    return power(path_length_prod, mpf(1.0) / mpf(path_length_count))


#####################################################
#MAIN BODY
#####################################################

signal.signal(signal.SIGINT, sigint_handler)
nodes.add(root_node)

if len(sys.argv) < 4:
    print_usage_and_die()
else:
    root_node_id = sys.argv[1]
    node_to_id[root_node] = root_node_id
    id_to_node[root_node_id] = root_node
    base_fee_threshold = int(sys.argv[2])
    permillion_fee_threshold = int(sys.argv[3])
    if len(sys.argv) >= 5:
        min_channels = int(sys.argv[4])
    if len(sys.argv) >= 6:
        min_capacity = int(sys.argv[5])

json_data = json.load(sys.stdin)
ln_software_type = detect_ln_software_type(json_data)
if ln_software_type == LNSoftwareType.UKN:
    sys.stderr.write("Valid JSON detected on stdin but it doesn't look like output from C-Lightning or LND. Please see usage below.\n\n")
    print_usage_and_die()
else:
    print("Found %s input JSON" % ln_software_type.value)
json_data_root = json_data["channels"] if ln_software_type == LNSoftwareType.CLI else json_data["edges"]

i = 1
num_inactive_channels = 0
for chan in json_data_root:
    if ln_software_type == LNSoftwareType.LND and (chan["node1_policy"] == None or chan["node2_policy"] == None):
        continue
    src_id = chan["source"] if ln_software_type == LNSoftwareType.CLI else chan["node1_pub"]
    if src_id not in id_to_node:
        node_to_id[i] = src_id
        id_to_node[src_id] = i
        nodes.add(i)
        i += 1
    src = id_to_node[src_id]

    dest_id = chan["destination"] if ln_software_type == LNSoftwareType.CLI else chan["node2_pub"]
    if dest_id not in id_to_node:
        node_to_id[i] = dest_id
        id_to_node[dest_id] = i
        nodes.add(i)
        i += 1
    dest = id_to_node[dest_id]

    if (ln_software_type == LNSoftwareType.CLI and not chan["active"]) or (ln_software_type == LNSoftwareType.LND and (chan["node1_policy"]["disabled"] or chan["node2_policy"]["disabled"])):
        num_inactive_channels += 1
        continue

    if src not in outgoing:
        outgoing[src] = set()
    outgoing[src].add(dest)
    if dest not in incoming:
        incoming[dest] = set()
    incoming[dest].add(src)

    if ln_software_type == LNSoftwareType.CLI:
        base_fee = chan["base_fee_millisatoshi"]
        permillion_fee = chan["fee_per_millionth"]
        chan_capacity[(src, dest)] = chan["satoshis"]
    else:
        base_fee = int(chan["node2_policy"]["fee_base_msat"])
        permillion_fee = int(chan["node2_policy"]["fee_rate_milli_msat"])
        chan_capacity[(src, dest)] = int(chan["capacity"])
    chan_fees[(src, dest)] = (permillion_fee, base_fee)

    if ln_software_type == LNSoftwareType.CLI:
        continue

    # LND specific: REVERSE DIRECTION node2=>node1, fees of node1_policy count
    if src not in incoming:
        incoming[src] = set()
    incoming[src].add(dest)
    if dest not in outgoing:
        outgoing[dest] = set()
    outgoing[dest].add(src)

    base_fee = int(chan["node1_policy"]["fee_base_msat"])
    permillion_fee = int(chan["node1_policy"]["fee_rate_milli_msat"])
    chan_fees[(dest, src)] = (permillion_fee, base_fee)
    chan_capacity[(dest, src)] = int(chan["capacity"])

if ln_software_type == LNSoftwareType.CLI and "nodes" in json_data:
    parse_node_aliases(json_data)

num_active_nodes = reduce(lambda x,y: x+y, map(lambda n: 1 if n in outgoing or n in incoming else 0, nodes))
print("%d/%d active/total nodes and %d/%d active/total (unidirectional) channels found." % (num_active_nodes, len(nodes), len(chan_fees) - num_inactive_channels, len(chan_fees)))
nodes.remove(root_node)

(lowfee_edges, lowfee_nodes, min_cost_to_node) = get_lowfee_reachable_subgraph()
existing_reachable_nodes = get_lowfee_reachable_unweighted_maxflows(lowfee_edges, lowfee_nodes)
maxflow_sum = reduce(lambda x,y: x+y, [n[1] for n in existing_reachable_nodes.items()])
maxflow_prod = reduce(lambda x,y: x*y, [mpf(n[1]) for n in existing_reachable_nodes.items()])
maxflow_mean = float(maxflow_sum) / float(len(existing_reachable_nodes))
maxflow_geomean = power(maxflow_prod, mpf(1.0) / mpf(len(existing_reachable_nodes)))
print("%d \"low-fee reachable\" nodes already exist with mean and geomean route diversity %f and %s." % (len(existing_reachable_nodes), maxflow_mean, nstr(maxflow_geomean, 6)))

asp = calculate_asp(lowfee_edges, lowfee_nodes)
print("Geomean of the shortest path from your node to each other low-fee reachable node = %s" % nstr(asp, 6))
ppm_geomean = get_lowfee_reachable_ppm_geomean(lowfee_nodes, min_cost_to_node)
print("Geomean of the cheapest total PPM fees from your node to each other low-fee reachable node = %s" % nstr(ppm_geomean, 6))

#Iterate over all other nodes, sorted by decreasing number of incoming channels under the theory that more connected nodes
#are more likely to have higher peer benefit, thus giving good answers more quickly
i = 0
nodes_num_outgoing = {n: len(outgoing[n]) if n in outgoing else 0 for n in nodes}
for n in [k for k, v in sorted(nodes_num_outgoing.items(), key = lambda x: x[1], reverse = True)]:
    if n in outgoing[root_node]:
        continue
    if not node_is_big_enough(n):
        continue
    if i % 100 == 0:
        if i == 0:
            print("Trying new peers.")
        else:
            print("Tried %d peers:\n----------" % i)
            print_top_new_peers(10)
            print("----------")
    (new_lowfee_edges, new_lowfee_nodes, min_cost_to_node) = get_lowfee_reachable_subgraph(n)
    asp = calculate_asp(new_lowfee_edges, lowfee_nodes)
    ppm_geomean = get_lowfee_reachable_ppm_geomean(lowfee_nodes, min_cost_to_node)
    now_reachable = get_lowfee_reachable_unweighted_maxflows(new_lowfee_edges, new_lowfee_nodes)
    maxflow_prod = mpf('1.0')
    num_new_nodes = 0
    routability_improvements = 0
    bonus = 0
    for r in now_reachable:
        if r in existing_reachable_nodes:
          maxflow_prod *= now_reachable[r]
        if r not in existing_reachable_nodes:
            num_new_nodes += 1
        elif now_reachable[r] > existing_reachable_nodes[r]:
            routability_improvements += 1
            if existing_reachable_nodes[r] < 3:
                bonus += 3 - existing_reachable_nodes[r]
    new_peer_benefit[n] = 3*num_new_nodes + routability_improvements + bonus
    maxflow_geomean = power(maxflow_prod, mpf('1.0') / mpf(len(existing_reachable_nodes)))
    peer_name = (node_to_alias[n] + " (%s)" % node_to_id[n][0:7]) if n in node_to_alias else node_to_id[n] 
    print("Peer %s has benefit %f with %d new low-fee reachable nodes and %d low-fee routability improvements, bonus %d; would make maxflow geomean %s, shortest path length geomean %s, and ppm geomean %s" % (peer_name, new_peer_benefit[n], num_new_nodes, routability_improvements, bonus, nstr(maxflow_geomean, 6), nstr(asp, 6), nstr(ppm_geomean, 6)))
    i += 1

print_top_new_peers(10)
