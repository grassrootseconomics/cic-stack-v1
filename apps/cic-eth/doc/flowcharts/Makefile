INPUTS = $(wildcard *.dot)
OUTPUTS = $(patsubst %.dot, %.png, $(INPUTS))

.SUFFIXES: .dot .png

.dot.png:
	dot -T png $(basename $@).dot > $@

all: $(OUTPUTS)

clean:
	rm -vf *.png

.PHONY: clean 

