PYINCLUDES = $(shell python3-config --includes)
PYLIBS = $(shell python3-config --libs)
CC = gcc
node_recommender: node_recommender.py
	cython -3 --embed node_recommender.py
	$(CC) $(PYINCLUDES) $(PYLIBS) -O3 -march=native -o node_recommender node_recommender.c

.PHONY: clean
clean:
	rm node_recommender
	rm node_recommender.c
