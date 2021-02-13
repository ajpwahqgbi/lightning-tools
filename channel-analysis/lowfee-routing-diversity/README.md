Low-fee Routing Diversity
----
This script attempts to measure, for each other LN node to which you don't already have a channel, the potential benefit to "low-fee routing diversity" from adding a channel to that peer. This is especially helpful for routing node operators who wish to allocate their capital wisely.

"Low-fee routing diversity" here is measured like so:
1. A reduced LN channel graph is produced, including only nodes which are "low-fee reachable" (i.e. there exists a path in the channel graph from your node to that node with total fees less than a specified maximum) and only edges satisying the restricted fee constraint.
2. An isomorphic graph is constructed with unit edge weights and the [maxflow](https://en.wikipedia.org/wiki/Maximum_flow_problem) from your node to each other node on the Lightning Network is computed. This maxflow is a rough metric for the diversity of paths (satisfying the restricted fee constraint) that exist between your node and the other node. Note that the maxflow here does *not* depend on the size of the channels along the paths or on the actual likelihood of those channels having capacity to route a payment.
3. Statistics are reported for each potential channel peer about how these maxflows would change: 

* How many new nodes become low-fee reachable if we peer with them
* How many nodes see an increased number of low-fee reachable paths ("routability improvements")
* How many nodes with fewer than 3 existing low-fee reachable paths get more low-fee reachable paths, with an improvement to a node with only 1 existing low-fee reachable path counting for 2 points

A geometric mean of the maxflows to each low-fee reachable node is reported. Note that while higher is better, it is possible for a good channel peer to reduce your maxflow geomean score. This just means that that peer has good low-fee access to part of the network, but does not help add low-fee reachable routes to most of the network. If you're already well-connected, it might be lucrative to peer with that node, despite the reduction in your maxflow geomean. This calculation should probably be fixed to only include existing low-fee reachable nodes in order to provide a better metric.

How to use it
----
* Install dependencies: `pip3 install PyMaxflow mpmath`
* Compile the script with Cython (optional): `make`
* Collect the LN channel graph at multiple times throughout the week: `lightning-cli listchannels >lnchannels.20210202`. You need to do this periodically because each one is a snapshot of the network, and because of dynamic fees and the shifting network, a good channel peer at one time may not be a good channel peer at other times. You want to peer with nodes that are consistently good choices over time.
* For each collected LN channel graph, analyze the graph for varying fee rates, e.g.: `<lnchannels.20210202 ./lowfee_routing_diversity.py <your node pubkey> 2033 250`, `<lnchannels.20210202 ./lowfee_routing_diversity.py <your node pubkey> 1050 150`, `<lnchannels.20210202 ./lowfee_routing_diversity.py <your node pubkey> 1010 75` (or with `./lowfee_routing_diversity` if you ran `make`).
* Note which prospective peers (identified by their pubkey) are consistently in the "top 10" nodes for varying fee rate threshholds and with varying snapshots of the LN channel graph.
* Open a channel to one or more of the most consistently high-rated proposed peers.
