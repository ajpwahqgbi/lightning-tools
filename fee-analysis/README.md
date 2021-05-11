# Overview
There are three tools here to analyze payment forwards, fees earned, and fees paid:
 - get\_period\_fees.py
 - get\_period\_rebalance\_cost.py
 - get\_period\_flows.py

## get\_period\_fees.py
This script reports the values for gross fee earnings, number of payments forwarded, and volume of BTC forwarded in the specified period.

## get\_period\_rebalance\_cost.py
This script looks for paid invoices from the [official C-Lightning rebalancing plugin](https://github.com/lightningd/plugins/tree/master/rebalance) (specifically, those invoices which have a label beginning with "Rebalance-") and reports the sum of fees paid for those rebalances.

## get\_period\_flows.py
This script pretty-prints a table with a per-channel breakdown of payments forwarded in and out of that channel, BTC forwarded in each direction, and fees earned from forwards in each direction. Note that fees reported for forwards incoming on each channel are not really earned; it is the outgoing channel for that forward that accrues the fees. The incoming fee statistics are reported to help illuminate which channels forward the juiciest forwarding volume to us.

# Monitoring one-liner
I like to run the following bash one-liner in a GNU screen session:

    BEGIN="May 01 2021"; NOW=$(date '+%s'); echo "-------"; while true; do date; lightning-cli listforwards | ./get_period_fees.py $(date '+%s' -d "$BEGIN") $NOW; (echo "{"; lightning-cli listpays | tail -n +2 | head -n -2; echo "],"; lightning-cli listinvoices | tail -n +2) | ./get_period_rebalance_cost.py $(date '+%s' -d "$BEGIN") $NOW; lightning-cli listforwards | ./get_period_flows.py $(date '+%s' -d "$BEGIN") $NOW; sleep 3600; done

