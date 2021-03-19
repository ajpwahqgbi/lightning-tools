#!/usr/bin/env python3
#Pipe input from `lightning-cli listchannels`
import sys, json
from functools import reduce

root_node = 0
root_node_id = "" 

#Define the "low fee" threshold
#These values are for the *total path* 
base_fee_threshold = 0
permillion_fee_threshold = 0

#Define the minimum channels and capacity requirements to consider a node for an outgoing channel
min_channels = 10
min_capacity = 15000000 #NOT about total capacity of a channel path

nodes = set()
node_to_id = dict()
id_to_node = dict()
chan_fees = {}
chan_capacity = {}
outgoing = {}
incoming = {}
new_peer_asp = {}

nodes.add(root_node)

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
    for (n, b) in sorted(new_peer_asp.items(), key = lambda x: x[1]):
        if n in incoming[root_node] or n in outgoing[root_node]:
            continue
        if not node_is_big_enough(n):
            continue

        print("%f ASP when peering with node %s" % (b, node_to_id[n]))
        cnt += 1
        if cnt >= num:
            break

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

    return (lowfee_edges, lowfee_nodes)

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
    path_length_sum = reduce(lambda x,y: x+y, map(lambda n: min_distance[n], filter(lambda n: True if n in min_distance else False, lowfee_nodes)))
    return float(path_length_sum)/len(lowfee_nodes)


#####################################################

if len(sys.argv) < 4:
    sys.stderr.write("Usage:\n")
    sys.stderr.write("lightning-cli listchannels | %s root_node base_fee permillion_fee [min_channels] [min_capacity]\n" % sys.argv[0])
    sys.stderr.write("\n")
    sys.stderr.write("Calculates your node's average shortest path to all other low-fee reachable nodes, then calculates it again")
    sys.stderr.write("as if you were to add a channel to each qualifying potential new channel peer.")
    sys.stderr.write("\n")
    sys.stderr.write("\n")
    sys.stderr.write("root_node: Your node pubkey\n")
    sys.stderr.write("base_fee: The maximum base fee (in milisatoshi) accumulated along a route to remain \"low-fee reachable\"\n")
    sys.stderr.write("permillion_fee: The maximum permillion fee accumulated along a route to remain \"low-fee reachable\"\n")
    sys.stderr.write("min_channels: The minimum number of channels a node must have to consider peering with it (optional, default %d)\n" % min_channels)
    sys.stderr.write("min_capacity: The minimum total capacity a node (in satoshi) must have to consider peering with it.  Unrelated to the capacity of channels along a route. (optional, default %d)\n" % min_capacity)
    sys.exit(1)
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

i = 1
num_inactive_channels = 0
for chan in json.load(sys.stdin)["channels"]:
    src_id = chan["source"]
    if src_id not in id_to_node:
        node_to_id[i] = src_id
        id_to_node[src_id] = i
        nodes.add(i)
        i += 1
    src = id_to_node[src_id]

    dest_id = chan["destination"]
    if dest_id not in id_to_node:
        node_to_id[i] = dest_id
        id_to_node[dest_id] = i
        nodes.add(i)
        i += 1
    dest = id_to_node[dest_id]

    if not chan["active"]:
        num_inactive_channels += 1
        continue

    if src not in outgoing:
        outgoing[src] = set()
    outgoing[src].add(dest)
    if dest not in incoming:
        incoming[dest] = set()
    incoming[dest].add(src)

    base_fee = chan["base_fee_millisatoshi"]
    permillion_fee = chan["fee_per_millionth"]
    chan_fees[(src, dest)] = (permillion_fee, base_fee)
    chan_capacity[(src, dest)] = chan["satoshis"]

num_active_nodes = reduce(lambda x,y: x+y, map(lambda n: 1 if n in outgoing or n in incoming else 0, nodes))
print("%d/%d active/total nodes and %d/%d active/total (unidirectional) channels found." % (num_active_nodes, len(nodes), len(chan_fees) - num_inactive_channels, len(chan_fees)))

nodes.remove(root_node)
(lowfee_edges, lowfee_nodes) = get_lowfee_reachable_subgraph()
asp = calculate_asp(lowfee_edges, lowfee_nodes)
print("Average shortest path from your node to all other low-fee reachable nodes = %f" % asp)

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
    (new_lowfee_edges, _) = get_lowfee_reachable_subgraph(n)
    asp = calculate_asp(new_lowfee_edges, lowfee_nodes)
    new_peer_asp[n] = asp
    print("Peer %s makes ASP %f" % (node_to_id[n], asp))
    i += 1

print_top_new_peers(10)
