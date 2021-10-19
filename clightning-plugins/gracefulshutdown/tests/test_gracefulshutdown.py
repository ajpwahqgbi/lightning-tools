from pyln.testing.fixtures import *
from pyln.testing import utils
from pyln.client import RpcError

import os
import pytest

# # Overload, so pyln.testing uses local development version of lightningd
# lightningd_path = 'path_to_your_local_lightningd_build'
#
# @pytest.fixture
# def node_cls():
#     return LightningNode
#
#
# class LightningNode(utils.LightningNode):
#     def __init__(self, *args, **kwargs):
#         utils.LightningNode.__init__(self, *args, **kwargs)
#         self.daemon.executable = lightningd_path


def test_htlc_free_shutdown(node_factory, executor):
    """l2 has an in-flight HTLC (paying itself) and we want it to shutdown cleanly
       , i.e. block new htlc's and resolve the in-flight one.

       We use a plugin with method `shutdown_cleanly`, when called it starts another
       plugin that injects custom behavior (using htlc_accepted hook) and finally
       calls RPC `stop` itself.
    """
    #
    l1, l2 = node_factory.line_graph(2, opts=[
        {'may_reconnect': True},
        {'may_reconnect': True,
         'plugin': [os.path.join(os.getcwd(), 'tests/hold_htlcs.py'),
                    os.path.join(os.getcwd(), 'shutdown_clean.py')]}
    ])

    i1 = l2.rpc.invoice(msatoshi=1000, label="i1", description="desc")['bolt11']
    f1 = executor.submit(l1.rpc.pay, i1)

    l2.daemon.wait_for_log(r'Holding onto an incoming htlc')

    # Check that the status mentions the HTLC being held
    l2.rpc.listpeers()
    peers = l2.rpc.listpeers()['peers']
    htlc_status = peers[0]['channels'][0]['htlcs'][0].get('status', None)
    assert htlc_status == "Waiting for the htlc_accepted hook of plugin hold_htlcs.py"

    # Plugin shutdown_clean.py does the self-destructing rpc.stop()
    with pytest.raises(RpcError):
        l2.rpc.call('shutdown_clean')

    assert(l2.daemon.is_in_log(r'Waiting for 1 HTLCs to resolve...'))
    utils.wait_for(lambda: not l2.daemon.running)
    l1.stop()

    # restarting l2, it should have no in-flight htlcs
    l2.start()
    peers_clean = l2.rpc.listpeers()['peers']
    assert(peers_clean[0]['channels'][0]['htlcs'] == [])
