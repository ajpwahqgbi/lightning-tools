PYINCLUDES = $(shell python3-config --includes)
PYLIBS = $(shell python3-config --libs)
CC = gcc
minimize_asp: minimize_asp.py
	cython -3 --embed minimize_asp.py
	$(CC) $(PYINCLUDES) $(PYLIBS) -O3 -march=native -o minimize_asp minimize_asp.c

.PHONY: clean
clean:
	rm minimize_asp
	rm minimize_asp.c
