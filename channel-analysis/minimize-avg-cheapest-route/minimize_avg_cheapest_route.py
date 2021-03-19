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
    sys.stderr.write("with C-Lightning: (echo \"{\"; lightning-cli listnodes | tail -n +2 | head -n -2; echo \"],\"; lightning-cli listchannels | tail -n +2) | %s root_node base_fee [min_channels] [min_capacity]\n" % sys.argv[0])
    sys.stderr.write("with LND: lncli describegraph | %s root_node base_fee [min_channels] [min_capacity]\n" % sys.argv[0])
    sys.stderr.write("\n")
    sys.stderr.write("root_node: Your node pubkey\n")
    sys.stderr.write("base_fee: The maximum base fee (in milisatoshi) accumulated along a route to remain \"low-fee reachable\"\n")
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

def get_lowfee_reachable_ppm_avg_geomean(proposed_new_peer=None, existing_nodes=None):
    cheapest_route = dict()
    lowfee_reachable = set()
    lowfee_edges = set()
    min_cost_to_node = dict() #maps to a set of fee tuples (permillion, base) of costs to reach that node
                              #that lie along the Pareto frontier (i.e, there is no other min_cost_to_node
                              #that is strictly worse on both permillion and base)
    processed_nodes = set()
    queued = set()
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

            if base_fee <= base_fee_threshold:
                lowfee_reachable.add(cur_node)
            else:
                continue

            if cur_node not in outgoing:
                continue

            for o in outgoing[cur_node]:
                (new_permillion_fee, new_base_fee) = chan_fees[(cur_node, o)]
                new_permillion_fee += permillion_fee
                new_base_fee += base_fee

                if new_base_fee <= base_fee_threshold:
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

    test_set = lowfee_reachable if existing_nodes is None else existing_nodes
    for cur_node in test_set:
        min_costs = min_cost_to_node[cur_node]
        mincost = sorted(min_costs, key = lambda x: x[0])[0]
        cheapest_route[cur_node] = mincost[0]

    ppm_sum = reduce(lambda x,y: x+y, [ppm for n, ppm in cheapest_route.items()])
    ppm_prod = reduce(lambda x,y: x*y, [ppm if ppm != 0 else 1 for n, ppm in cheapest_route.items()])
    ppm_mean = float(ppm_sum) / float(len(cheapest_route))
    ppm_geomean = power(ppm_prod, mpf(1.0) / mpf(len(cheapest_route)))

    return (ppm_mean, nstr(ppm_geomean, 6), test_set)


#####################################################
#MAIN BODY
#####################################################

signal.signal(signal.SIGINT, sigint_handler)
nodes.add(root_node)

if len(sys.argv) < 3:
    print_usage_and_die()
else:
    root_node_id = sys.argv[1]
    node_to_id[root_node] = root_node_id
    id_to_node[root_node_id] = root_node
    base_fee_threshold = int(sys.argv[2])
    if len(sys.argv) >= 4:
        min_channels = int(sys.argv[3])
    if len(sys.argv) >= 5:
        min_capacity = int(sys.argv[4])

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

(existing_ppm_avg, existing_ppm_geomean, existing_reachable) = get_lowfee_reachable_ppm_avg_geomean()
print("Current ppm feerate (mean, geomean) under %dmsat base fee threshold is (%f, %s)." % (base_fee_threshold, existing_ppm_avg, existing_ppm_geomean))

#Iterate over all other nodes, sorted by decreasing number of incoming channels under the theory that more connected nodes
#are more likely to have higher peer benefit, thus giving good answers more quickly
i = 0
nodes_num_outgoing = {n: len(outgoing[n]) if n in outgoing else 0 for n in nodes}
for n in [k for k, v in sorted(nodes_num_outgoing.items(), key = lambda x: x[1], reverse = True)]:
    if n in outgoing[root_node]:
        continue
    if not node_is_big_enough(n):
        continue
    (new_ppm_avg, new_ppm_geomean, _) = get_lowfee_reachable_ppm_avg_geomean(n, existing_reachable)
    peer_name = (node_to_alias[n] + " (%s)" % node_to_id[n][0:7]) if n in node_to_alias else node_to_id[n] 
    print("Peer %s makes ppm feerate (mean, geomean) = (%f, %s)." % (peer_name, new_ppm_avg, new_ppm_geomean))
    i += 1
