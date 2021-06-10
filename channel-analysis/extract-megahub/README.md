This script reads the LN channel graph and starts with a seed megahub set specified on the command line. It iteratively searches for nodes not already in the megahub set that make at least `N` triangles with a node in the megahub. Those nodes are added to the megahub set and the search begins again. Once a search iteration rejects all candidate nodes, the algorithm is finished and the complete megahub set is returned.

Usage
----
`./megahub.py <N> <node_id> [node_id ...]`

- `N` is the number of triangles to the existing megahub set that a new node must have in order to be added to the megahub set.
- At least one `node_id` (node pubkey) must be provided to seed the megahub set.
