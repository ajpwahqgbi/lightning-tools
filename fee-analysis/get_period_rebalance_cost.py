#!/usr/bin/python3
import sys
import json
from datetime import date

def print_usage_and_die():
    sys.stderr.write("Usage:\n")
    sys.stderr.write("(echo \"{\"; lightning-cli listpays | tail -n +2 | head -n -2; echo \"],\"; lightning-cli listinvoices | tail -n +2) | %s $(date '+%%s' -d \"Jan 01 2021\") $(date '+%%s' -d \"Feb 01 2021\")\n" % sys.argv[0])
    sys.stderr.write("\n")
    sys.stderr.write("Calculates your C-Lightning node's rebalancing fees in the specified period.\n")
    sys.stderr.write("\n")
    sys.exit(1)

if len(sys.argv) < 3:
    print_usage_and_die()

epoch_begin = int(sys.argv[1])
epoch_end = int(sys.argv[2])

if epoch_end <= epoch_begin:
    print_usage_and_die()

rebalance_payment_hashes = set()
fees_paid = 0
json_in = json.load(sys.stdin)
for invoice in json_in["invoices"]:
    if invoice["status"] == "paid":
        pay_time = int(invoice["paid_at"])
        if invoice["label"].startswith("Rebalance-") and pay_time >= epoch_begin and pay_time <= epoch_end:
            rebalance_payment_hashes.add(invoice["payment_hash"])
for payment in json_in["pays"]:
    if payment["payment_hash"] in rebalance_payment_hashes and payment["status"] == "complete":
        amount_sent = int((payment["amount_sent_msat"])[:-4])
        amount = int((payment["amount_msat"])[:-4])
        fees_paid = fees_paid + (amount_sent - amount)

print("Paid %.3f satoshis for channel rebalancing between %s and %s." % (float(fees_paid) / 1000.0, date.fromtimestamp(epoch_begin), date.fromtimestamp(epoch_end)))
