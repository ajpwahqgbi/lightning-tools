This script reads the LN channel graph and starts with a seed megahub set specified on the command line. It iteratively searches for nodes not already in the megahub set that make at least `N` triangles with a node in the megahub. Those nodes are added to the megahub set and the search begins again. Once a search iteration rejects all candidate nodes, the algorithm is finished and the complete megahub set is returned.

Usage
----
`./megahub.py <N> <node_id> [node_id ...]`

- `N` is the number of triangles to the existing megahub set that a new node must have in order to be added to the megahub set.
- At least one `node_id` (node pubkey) must be provided to seed the megahub set.

Results
----
The reddit megahub, partially selected from [reddit user /u/schulze1's reddit megahub visualizer](https://megahub.satoshis.tech), as of June 11 2021:
```
user@host:~$ ./megahub.py 6 02241407b77092b0ac43350fdb09d13476cf11b0453037494e55f56207e1b247b8 026fb4507b229d692e6975d957610fc1a574cfc8085fd89bf967c18121b1b02132 02a20247f515d978cbf9e9ce6a4287b5931d724068b7b88bbaead6380db3dd8e9a 02a4002deca0ad6781b1c55ea5c692faae768fef44e1997c5723cb5393a98709ae 02dde1de894345d7167db18ff92266fa7302ae018fbea3b12948b3a50cf253f6db 02e0af3c70bf42343316513e54683b10c01d906c04a05dfcd9479b90d7beed9129 0337579aadc81356ed7f32587565e4c2a7f8d1561be8cc3bd976cbc6a409a4a71b 03f360457d29f50a1fe2d5b2e603207377f1676b335546622c182b086259615755
1088 nodes in the megahub:
[...]
average shortest path in the megahub is 2.10629
average shortest path for megahub nodes in the wider LN is 4.23984
average shortest path for non-megahub nodes in the wider LN is 10.2193
average shortest path in the wider LN is 8.20459
```
