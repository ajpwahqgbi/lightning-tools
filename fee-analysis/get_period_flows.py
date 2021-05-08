#!/usr/bin/python3
import sys
import json
from datetime import datetime

channels = set() # a bag of scids
channel_fees_collected = dict() # scid -> (x, y) where x = fees from this channel as input, y = fees from this channel as output
msat_moved = dict() # scid -> ((n, x), (n, y)) where x = msat moved in all forwards with this channel as input, y = msat moved " as output and n in both cases is the number of forwarding events

def print_usage_and_die():
    sys.stderr.write("Usage:\n")
    sys.stderr.write("lightning-cli listforwards | %s $(date '+%%s' -d \"Apr 01 2021\") $(date '+%%s' -d \"May 01 2021\")\n" % sys.argv[0])
    sys.stderr.write("\n")
    sys.stderr.write("Analyzes forwarding history and reports flow and fee statstics per channel.\n")
    sys.stderr.write("\n")
    sys.stderr.write("Note that fees are double-reported, once for the incoming channel and\n")
    sys.stderr.write("once for the outgoing channel of the payment forward from which we collected\n")
    sys.stderr.write("the fee.\n")
    sys.stderr.write("\n")
    sys.exit(1)

if len(sys.argv) != 3:
    print_usage_and_die()

epoch_begin = int(sys.argv[1])
epoch_begin_str = datetime.utcfromtimestamp(epoch_begin).strftime('%Y-%m-%d %H:%M:%S')
epoch_end = int(sys.argv[2])
epoch_end_str = datetime.utcfromtimestamp(epoch_end).strftime('%Y-%m-%d %H:%M:%S')

json_in = json.load(sys.stdin)

#get flow statistics:
for forward in json_in["forwards"]:
    fwd_time = forward["received_time"]
    if forward["status"] == "settled" and fwd_time >= epoch_begin and fwd_time <= epoch_end:
        in_scid = forward["in_channel"]
        out_scid = forward["out_channel"]
        fee = int(forward["fee_msat"][:-4])

        channels.add(in_scid)
        channels.add(out_scid)

        in_amt = int(forward["in_msat"][:-4])
        flow = ((1, in_amt), (0, 0))
        if in_scid in msat_moved:
            flow = msat_moved[in_scid]
            flow = ((flow[0][0] + 1, flow[0][1] + in_amt), flow[1])
        msat_moved[in_scid] = flow

        out_amt = int(forward["out_msat"][:-4])
        flow = ((0, 0), (1, out_amt))
        if out_scid in msat_moved:
            flow = msat_moved[out_scid]
            flow = (flow[0], (flow[1][0] + 1, flow[1][1] + out_amt))
        msat_moved[out_scid] = flow

        fees_collected_chanin = (fee, 0)
        if in_scid in channel_fees_collected:
            fees_collected_chanin = (channel_fees_collected[in_scid][0] + fee, channel_fees_collected[in_scid][1])
        channel_fees_collected[in_scid] = fees_collected_chanin

        fees_collected_chanout = (0, fee)
        if out_scid in channel_fees_collected:
            fees_collected_chanout = (channel_fees_collected[out_scid][0], channel_fees_collected[out_scid][1] + fee)
        channel_fees_collected[out_scid] = fees_collected_chanout

#report statistics for channels:
print("-------")
print("For payment forwards between %s and %s:\n" % (epoch_begin_str, epoch_end_str))
for scid in sorted(channels, key = lambda s: msat_moved[s][0][1] + msat_moved[s][1][1]):
    collected_fees = channel_fees_collected[scid]
    moved = msat_moved[scid]
    print("channel %s moved (%4d in, %4d out) (%9.3f, %9.3f) ksat, earning (%9.3f, %9.3f) sat fees" % (scid.rjust(13), moved[0][0], moved[1][0], moved[0][1] / 1000000.0, moved[1][1] / 1000000.0, collected_fees[0] / 1000.0, collected_fees[1] / 1000.0))
print("-------")

