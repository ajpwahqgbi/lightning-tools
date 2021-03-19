PYINCLUDES = $(shell python3-config --includes)
PYLIBS = $(shell python3-config --libs)
CC = gcc
minimize_avg_cheapest_route: minimize_avg_cheapest_route.py
	cython -3 --embed minimize_avg_cheapest_route.py
	$(CC) $(PYINCLUDES) $(PYLIBS) -O3 -march=native -o minimize_avg_cheapest_route minimize_avg_cheapest_route.c

.PHONY: clean
clean:
	rm minimize_avg_cheapest_route
	rm minimize_avg_cheapest_route.c
