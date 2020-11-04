FROM gcc:latest AS ccl-glove-builder
WORKDIR /usr/src/app
COPY submodules/ccl/ ccl/
COPY submodules/glove/ glove/
RUN cd ccl/ && make CPPFLAGS='$(COPT) $(CDEBUG) $(INCLUDES) -std=c++0x -fpermissive -Wno-narrowing'
RUN cd glove && make

FROM openjdk:7 AS bmm-builder
WORKDIR /usr/src/app
COPY submodules/BMM_labels/ BMM_labels/
RUN mkdir bmm && \
       cd BMM_labels && \
       javac -d ../bmm *.java -Xlint:deprecation && \
       cd ../bmm && \
       jar cfe BMM.jar BMM_labels/Main *

FROM nvidia/cuda:10.2-base AS grammar-induction
COPY --from=python:3.6-slim / /
WORKDIR /usr/src/app
COPY submodules/diora/ pipeline/diora
COPY --from=openjdk:slim / /
ENV JAVA_HOME=/usr/local/openjdk-14/
ENV PATH=${JAVA_HOME}/bin:${PATH}
COPY --from=ccl-glove-builder /usr/src/app/ccl/main/UnknownOS/cclparser pipeline/ccl/cclparser
COPY --from=ccl-glove-builder /usr/src/app/glove pipeline/glove
COPY --from=bmm-builder /usr/src/app/bmm/BMM.jar pipeline/bmm/BMM.jar
RUN apt-get update && apt-get install -y --no-install-recommends ed tk-dev build-essential && \
    pip install allennlp==0.9.0 torchvision==0.5.0 && \
    umask 0000 && mkdir logs && \
    # Make size of image smaller
    apt purge -y build-essential && \
    apt autoremove -y && \
    apt clean && \
    rm -rf /var/lib/apt/lists/*
COPY utils/ utils/
COPY scripts/ scripts/
COPY data/demo_language.txt data/demo_language.txt
ENTRYPOINT ["/bin/bash", "scripts/run_induce_grammar.sh"]
CMD ["demo_language","diora","--analysis"]
