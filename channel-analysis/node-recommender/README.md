Node recommender
----
This script attempts to measure, for each other LN node to which you don't already have a channel, the potential benefit to creating a channel with that node. To do this, it calculates various metrics about your node and how those metrics would change if you added a channel with each potential new channel peer. These metrics include:
* Low-fee routing diversity (see below)
* ~~Low-fee routing capacity~~ TODO
* Average shortest path
* Average cheapest path ppm cost

###Low-fee routing diversity
"Low-fee routing diversity" here is measured like so:
1. A reduced LN channel graph is produced, including only nodes which are "low-fee reachable" (i.e. there exists a path in the channel graph from your node to that node with total fees less than a specified maximum) and only edges satisying the restricted fee constraint.
2. An isomorphic graph is constructed with unit edge weights and the [maxflow](https://en.wikipedia.org/wiki/Maximum_flow_problem) from your node to each other node on the Lightning Network is computed. This maxflow is a rough metric for the diversity of paths (satisfying the restricted fee constraint) that exist between your node and the other node. Note that the maxflow here does *not* depend on the size of the channels along the paths or on the actual likelihood of those channels having capacity to route a payment.
3. Statistics are reported for each potential channel peer about how these maxflows would change: 

* How many new nodes become low-fee reachable if we peer with them
* How many nodes see an increased number of low-fee reachable paths ("routability improvements")
* How many nodes with fewer than 3 existing low-fee reachable paths get more low-fee reachable paths, with an improvement to a node with only 1 existing low-fee reachable path counting for 2 points

Finally, a geometric mean of the maxflows to each existing low-fee reachable node is reported. Higher is better.

###Low-fee routing capacity
TODO - we will run maxflow on a capacity-weighted low-fee reachable subgraph. Higher is better.

###Average shortest path
This is the geometric mean of the lengths of the shortest paths from your node to each other low-fee reachable node.
Lower is better.

###Average cheapest path ppm cost
This is the geometric mean of the total PPM feerate accumulated along the cheapest paths from your node to each other low-fee reachable node. Lower is better. NOTE: Take this metric with a hint of salt until I figure out why it is sometimes reported as *greater*when peering with some node than the existing PPM geomean.

How to use it
----
* Install dependencies: `pip3 install PyMaxflow mpmath`
* Compile the script with Cython (optional): `make`
* Collect the LN channel graph at multiple times throughout the week: `lightning-cli listchannels >lnchannels.20210202`. You need to do this periodically because each one is a snapshot of the network, and because of dynamic fees and the shifting network, a good channel peer at one time may not be a good channel peer at other times. You want to peer with nodes that are consistently good choices over time.
* For each collected LN channel graph, analyze the graph for varying fee rates, e.g.: `(echo "{"; lightning-cli listnodes | tail -n +2 | head -n -2; echo "],"; cat lnchannels.20210202 | tail -n +2) | ./node_recommender.py <your node pubkey> 2033 250`, `(echo "{"; lightning-cli listnodes | tail -n +2 | head -n -2; echo "],"; cat lnchannels.20210202 | tail -n +2) | ./node_recommender.py <your node pubkey> 1050 150`, `(echo "{"; lightning-cli listnodes | tail -n +2 | head -n -2; echo "],"; cat lnchannels.20210202 | tail -n +2) | ./node_recommender.py <your node pubkey> 1010 75` (or with `./node_recommender` if you ran `make`).
* Note which prospective peers are consistently well-scoring for varying fee rate threshholds and with varying snapshots of the LN channel graph.
* Open a channel to one or more of those proposed peers.
