#!/usr/bin/python3
import sys
import json
from datetime import date

def print_usage_and_die():
    sys.stderr.write("Usage:\n")
    sys.stderr.write("lightning-cli listforwards | %s $(date '+%%s' -d \"Jan 01 2021\") $(date '+%%s' -d \"Feb 01 2021\")\n" % sys.argv[0])
    sys.stderr.write("\n")
    sys.stderr.write("Calculates your C-Lightning node's collected fees in the specified period.\n")
    sys.stderr.write("\n")
    sys.exit(1)

if len(sys.argv) < 3:
    print_usage_and_die()

epoch_begin = int(sys.argv[1])
epoch_end = int(sys.argv[2])

if epoch_end <= epoch_begin:
    print_usage_and_die()

fees_earned = 0
num_forwards = 0
total_amt = 0
for forward in json.load(sys.stdin)["forwards"]:
    fwd_time = int(forward["received_time"])
    if forward["status"] == "settled":
        if fwd_time >= epoch_begin and fwd_time <= epoch_end:
            fees_earned = fees_earned + forward["fee"]
            num_forwards = num_forwards + 1
            total_amt += int(forward["out_msatoshi"])

print("Collected %.3f satoshis in fee payments from %d forwards totaling %.8fBTC between %s and %s." % (float(fees_earned) / 1000.0, num_forwards, total_amt / 100000000000.0, date.fromtimestamp(epoch_begin), date.fromtimestamp(epoch_end)))
