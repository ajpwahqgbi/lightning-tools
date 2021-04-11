Channel Opening Firewall
----
This plugin prevents other nodes from opening a channel to your node unless you explicitly whitelist them. To whitelist a node, you need to edit the plugin and add the node id/pubkey to `plugin.allowed_node_ids`, e.g. `plugin.allowed_node_ids = {"033d8656219478701227199cbd6f670335c8d408a92ae88b962c49d4dc0e83e025"}`. Then stop and start the plugin, or restart C-Lightning.
