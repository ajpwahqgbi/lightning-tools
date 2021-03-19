PYINCLUDES = $(shell python3-config --includes)
PYLIBS = $(shell python3-config --libs)
CC = gcc
lowfee_routing_diversity: lowfee_routing_diversity.py
	cython -3 --embed lowfee_routing_diversity.py
	$(CC) $(PYINCLUDES) $(PYLIBS) -O3 -march=native -o lowfee_routing_diversity lowfee_routing_diversity.c

.PHONY: clean
clean:
	rm lowfee_routing_diversity
	rm lowfee_routing_diversity.c
