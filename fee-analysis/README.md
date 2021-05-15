# Overview
There are three tools here to analyze payment forwards, fees earned, and fees paid:
 - get\_period\_fees.py
 - get\_period\_rebalance\_cost.py
 - get\_period\_pnl.py

## get\_period\_fees.py
This script reports the values for gross fee earnings, number of payments forwarded, and volume of BTC forwarded in the specified period.

## get\_period\_rebalance\_cost.py
This script looks for paid invoices from the [official C-Lightning rebalancing plugin](https://github.com/lightningd/plugins/tree/master/rebalance) (specifically, those invoices which have a label beginning with "Rebalance-") and reports the sum of fees paid for those rebalances.

## get\_period\_pnl.py
This script pretty-prints a table with a per-channel breakdown of payments forwarded in and out of that channel, BTC forwarded in each direction, fees earned from forwards in each direction, and rebalancing costs in each direction.

Note that fees reported for forwards incoming on each channel are not really earned; it is the outgoing channel for that forward that accrues the fees. The incoming fee and rebalancing cost statistics are reported to help illuminate which channels are helping to profitably forward payments and which are not.

## get\_period\_flows.py
Deprecated. Please use get\_period\_pnl.py instead.

# One-liners
I like to run the following bash one-liner in a GNU screen session to monitor the current month's operations:

    BEGIN=$(date '+%s' -d "May 01 2021"); while true; do date; NOW=$(date '+%s'); lightning-cli listforwards | ./get_period_fees.py $BEGIN $NOW; (echo "{"; lightning-cli listpays | tail -n +2 | head -n -2; echo "],"; lightning-cli listinvoices | tail -n +2) | ./get_period_rebalance_cost.py $BEGIN $NOW; ./get_period_pnl.py $BEGIN $NOW; sleep 3600; echo "----------"; done

The following one-liner similarly monitors the previous 30 days (2592000 seconds) of history:

    while true; do date; NOW=$(date '+%s'); BEGIN=$(($NOW - 2592000)); lightning-cli listforwards | ./get_period_fees.py $BEGIN $NOW; (echo "{"; lightning-cli listpays | tail -n +2 | head -n -2; echo "],"; lightning-cli listinvoices | tail -n +2) | ./get_period_rebalance_cost.py $BEGIN $NOW; ./get_period_pnl.py $BEGIN $NOW; sleep 3600; echo "----------"; done

