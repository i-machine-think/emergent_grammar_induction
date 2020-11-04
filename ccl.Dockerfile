FROM gcc:latest AS ccl-glove-builder
WORKDIR /usr/src/app
COPY submodules/ccl/ ccl/
RUN cd ccl/ && make CPPFLAGS='$(COPT) $(CDEBUG) $(INCLUDES) -std=c++0x -fpermissive -Wno-narrowing'

FROM openjdk:7 AS bmm-builder
WORKDIR /usr/src/app
COPY submodules/BMM_labels/ BMM_labels/
RUN mkdir bmm && \
       cd BMM_labels && \
       javac -d ../bmm *.java -Xlint:deprecation && \
       cd ../bmm && \
       jar cfe BMM.jar BMM_labels/Main *

FROM openjdk:slim AS grammar-induction
COPY --from=python:3.6-slim / /
WORKDIR /usr/src/app
COPY --from=ccl-glove-builder /usr/src/app/ccl/main/UnknownOS/cclparser pipeline/ccl/cclparser
COPY --from=bmm-builder /usr/src/app/bmm/BMM.jar pipeline/bmm/BMM.jar
RUN apt-get update && \
    apt-get install --no-install-recommends -y ed tk-dev && \
    pip install numpy argparse nltk && \
    # Make log directory
    umask 0000 && mkdir logs && \
    # Make size of image smaller
    apt autoremove -y && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*
COPY utils/ utils/
COPY scripts/ scripts/
COPY data/demo_language.txt data/demo_language.txt
ENTRYPOINT ["/bin/bash", "scripts/run_induce_grammar.sh"]
CMD ["demo_language","ccl","--analysis"]
