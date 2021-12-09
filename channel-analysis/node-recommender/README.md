# Node recommender
This script attempts to measure, for each other LN node to which you don't already have a channel, the potential benefit to creating a channel with that node. To do this, it calculates various metrics about your node and how those metrics would change if you added a channel with each potential new channel peer. These metrics include:
* Low-fee routing diversity (see below)
* ~~Low-fee routing capacity~~ TODO
* Average shortest path
* Average cheapest path ppm cost

### Low-fee routing diversity
"Low-fee routing diversity" is the geometric mean of all edge-disjoint maxflows between the root node (i.e. your node) and each other low-fee reachable LN node, calculated on the (unit-capacity) low-fee reachable subgraph. In other words:
1. A reduced LN channel graph is produced. In this reduced graph, only "low-fee reachable" nodes and channels are included. A channel is low-fee reachable if there exists at least one path in the channel graph starting from the root node and traversing that channel, for which the total accumulated base and PPM channel fees are below a specified maximum. Similarly, a node is low-fee reachable if at least one of its channels is low-fee reachable.
2. The [maxflow](https://en.wikipedia.org/wiki/Maximum_flow_problem)s on this reduced channel graph from the root node to each other low-fee reachable node are computed, using unit edge capacities. Each maxflow is a rough metric for the diversity of reasonable paths that exist between the root node and the other node. Note that the maxflow does *not* depend on the size of the channels along the paths or on the actual likelihood of those channels having capacity to route a payment. Note also that not all possible paths in the low-fee reachable subgraph satisfy the low-fee constraint.
3. The geometric mean of these maxflows is computed and reported, along with other statistics about how these maxflows would change:

* How many new nodes become low-fee reachable if we peer with them ("newly reachable")
* How many nodes see an increased number of low-fee reachable paths ("routability improvements")
* How many nodes with fewer than 3 existing low-fee reachable paths get more low-fee reachable paths, with an improvement to a node with only 1 existing low-fee reachable path counting for 2 points ("bonus")

For all of these statistics, higher is better.

### Low-fee routing capacity
TODO - we will run maxflow on the low-fee reachable subgraph with integer capacities. Higher is better.

### Average shortest path
This is the geometric mean of the lengths of the shortest paths from your node to each other low-fee reachable node.
Lower is better.

### Average cheapest path ppm cost
This is the geometric mean of the total PPM feerate accumulated along the cheapest paths from your node to each other low-fee reachable node. Lower is better. NOTE: Take this metric with a hint of salt until I figure out why it is sometimes reported as *greater*when peering with some node than the existing PPM geomean.

# How to use it
* Install dependencies: `pip3 install PyMaxflow mpmath`
* Compile the script with Cython (optional): `make`
* Collect the LN channel graph at multiple times throughout the week: . You need to do this periodically because each one is a snapshot of the network, and because of dynamic fees and the shifting network, a good channel peer at one time may not be a good channel peer at other times. You want to peer with nodes that are consistently good choices over time.
    - C-Lightning: `lightning-cli listchannels >lnchannels.20211207`
    - LND: `lncli describegraph >lnchannes.20211207`
* Run the script multiple times to analyze the channel graph at various fee rates:
    - C-Lightning: `(echo "{"; lightning-cli listnodes | tail -n +2 | head -n -2; echo "],"; cat lnchannels.20211207 | tail -n +2) | ./node_recommender.py <your node pubkey> 2033 250`, where 2033 and 250 are the base and ppm feerate thresholds and should be changed for each run.
    - LND: `cat lnchannels.20211207 | ./node_recommender.py <your node pubkey> 2033 250`, where 2033 and 250 are the base and ppm feerate thresholds and should be changed for each run.
* Save the output in files and use the included `analyze.py` to generate summaries. Note which prospective peers are consistently well-scoring for varying fee rate threshholds and with varying snapshots of the LN channel graph.
* Open a channel to one or more of those proposed peers.

Note that node aliases are only supported when used with C-Lightning; reports when using LND identify nodes exclusively by node ID.
