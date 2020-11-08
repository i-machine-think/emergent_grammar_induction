# emergent_grammar_induction

![GitHub](https://img.shields.io/github/license/i-machine-think/emergent_grammar_induction)
[![Docker Image](https://img.shields.io/static/v1?label=image&message=Docker&color=1488C6&logo=docker)](https://hub.docker.com/r/oskarvanderwal/emergent-grammar-induction)

> A toolkit for finding and analysing the grammars of emergent languages.

This repository contains a two-stage grammar induction setup for analysing languages emerging in referential and other games.
`emergent_grammar_induction` accompanies the paper ["The grammar of emergent languages"](https://arxiv.org/abs/2010.02069).

## Table of contents
* [Overview](#overview)
* [Requirements](#requirements)
* [Quick start](#quick-start)
* [Setup](#setup)
  * [Using DIORA](#using-diora)
  * [Data](#data)
  * [Optional flags](#optional-flags)
  * [Grammar analysis](#grammar-analysis)
* [Examples](#examples)
* [Reproduce our paper](#reproduce-our-paper)
* [Build EGI yourself](#build-egi-yourself)
* [Troubleshooting](#troubleshooting)

## Overview
You can use `emergent_grammar_induction` for analysing the syntactic structures of an emergent language.
Given a set of messages from this language, a probabilistic context free grammar (PCFG) is inferred.
The resulting grammar is further analysed to study the syntactic properties of the emergent language.

Because `emergent_grammar_induction` does not require any information on the setting of the language emergence, this analysis framework is not limited to certain games and input scenarios.

`emergent_grammar_induction` relies on several *unsupervised grammar induction* techniques.
In a two-stage setup either [`CCL`](https://www.aclweb.org/anthology/P07-1049.pdf) or [`DIORA`](https://arxiv.org/pdf/1904.02142) are used for inducing the constituency structure and [`BMM`](https://eprints.illc.uva.nl/274/1/PP-2007-40.text.pdf) for labelling this structure.

## Requirements
The recommended (and supported) way to use the grammar induction setup is by using [Docker](https://www.docker.com/), since this setup consists of multiple modules implemented in different programming languages by different people.

- [`Docker`](https://docs.docker.com/get-docker/)
- [`nvidia-container-toolkit`](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#install-guide) (*optional*: required for constituency parser DIORA)
- `CUDA` (*optional*: required for constituency parser DIORA)

## Quick start
Assuming you have your messages in `./data/messages.txt` (for each row a message) and you want the resulting PCFG and analysis results in `./results/`, run the following while you are in the root directory:

```
docker run --rm \
	-v $(pwd)/data:/usr/src/app/data \
	-v $(pwd)/results/:/usr/src/app/results/grammars \
	oskarvanderwal/emergent-grammar-induction messages ccl
```

What these flags mean:
- `-v`: create [volumes](https://docs.docker.com/storage/volumes/) with `data/` and `results/` such that the grammar induction can access these directories.
- `oskarvanderwal/emergent-grammar-induction`: name of the docker image.
- `messages`: refers to the message file `messages.txt` in `data/` containing the induction set; note that the extension `.txt` is left out, see [Data](#data) for more details.
- `ccl`: name of the constituency parser.

## Setup

The emergent grammar induction setup finds a grammar (e.g. `language.pcfg`) using the messages of an emergent language (e.g. found in `language.txt`).
For the constituency structure induction either [CCL](www.seggu.net/ccl/) or [DIORA](https://github.com/iesl/diora) (with [GloVe](https://nlp.stanford.edu/projects/glove/) embeddings) is used; the constituency labelling is done with [BMM](https://github.com/pld/BMM_labels/).
Optionally the resulting grammars are evaluated on various metrics, such as the description lengths (GDL and DDL) and the coverage.

The following diagram shows the pipeline of `emergent_grammar_induction`:
```
+---------------------------------+     +------------------------------+     +---------------------+
|  Input (emergent language)      |     |  Emergent Grammar Induction  |     |  Grammar analysis   |
+---------------------------------+     +------------------------------+     +---------------------+
| ./                              |     |  Constituency parser:        |     |  Induced grammar:   |
| ├── data/                       |     |    - CCL; or                 |     |    - language.pcfg  |
| │   ├── language.txt            +---->|    - DIORA (with GloVe).     +---->|  Evaluation:        |
| │   ├── language_eval.txt       |     |  Constituency labelling:     |     |    - GDL/DDL,       |
| │   ├── language_full.txt       |     |    - BMM.                    |     |    - coverage.      |
+---------------------------------+     +------------------------------+     +---------------------+
```

We have packaged the emergent grammar induction code in a Docker image that you can find on the Docker Hub: [`emergent-grammar-induction`](https://hub.docker.com/r/oskarvanderwal/emergent-grammar-induction).
There are two versions of the image, referred by:
- `oskarvanderwal/emergent-grammar-induction`: the default image that only provides the CCL constituency parser.
- `oskarvanderwal/emergent-grammar-induction:diora`: if you want to use DIORA as well, use the tag `diora`; this is a larger image and requires CUDA. Please refer to [Using DIORA](#using-diora) for more information.

The basic format of running the emergent grammar induction in the shell using CCL, is:

```
docker run --rm \
	-v $(pwd)/data:/usr/src/app/data \
	-v $(pwd)/results/:/usr/src/app/results/grammars \
	-v $(pwd)/logs:/usr/src/app/logs \
	oskarvanderwal/emergent-grammar-induction <name_message_file> ccl \
	[optional flags]
```

What these flags mean:
- `-v`: create [volumes](https://docs.docker.com/storage/volumes/) with `data/`, `results/` and `logs/`, such that the grammar induction can access these directories inside the Docker container.
  - `data/` contains the file `<name_message_file>.txt`.
  - The resulting grammar can be found in `results/ccl/<name_message_file>.pcfg`.
  - Logs can be found in timestamped directory in `logs/` (e.g. `logs/13-10-2020__18-49-19/`).
- `oskarvanderwal/emergent-grammar-induction`: name of the docker image.
- `<name_message_file>`: name of the message file in `data/` containing the induction set *without** `.txt`; see [Data](#data) for more details on how to prepare the data.
- `ccl`: name of the constituency parser (`ccl`); if you want to use `diora`, the format is slightly different (see [Using DIORA](#using-diora)).
- `[optional flags]`: please refer to [Optional flags](#optional-flags) for the options.

### Using DIORA

We have packaged DIORA in a separate image (`oskarvanderwal/emergent-grammar-induction:diora`), because it considerably increases the image size and requires access to a GPU.

To use DIORA, first make sure you have installed both `nvidia-container-toolkit` and `CUDA` on your machine.
You can test whether NVIDIA/CUDA works in Docker with:

```
docker run --rm --gpus all nvidia/cuda:10.2-base nvidia-smi
```

If that works, you can use the following format for using either DIORA or CCL for inducing a grammar:

```
docker run --rm --gpus all \
	-v $(pwd)/data:/usr/src/app/data \
	-v $(pwd)/results/:/usr/src/app/results/grammars \
	-v $(pwd)/logs:/usr/src/app/logs \
	oskarvanderwal/emergent-grammar-induction:diora <name_file> <name_parser> \
	[optional flags]
```

What these flags mean:
- `--gpus all`: indicates that Docker should have access to your GPUs.
- `-v`: create [volumes](https://docs.docker.com/storage/volumes/) with `data/`, `results/` and `logs/`, such that the grammar induction can access these directories.
- `oskarvanderwal/emergent-grammar-induction:diora`: name of the docker image; the tag `diora` indicates that DIORA is available.
- `<name_message_file>`: name of the .txt file in `data/` containing the induction set, **but without .txt**; e.g. `demo_language`; see [Data](#data).
- `<name_parser>`: name of the constituency parser; either `ccl` or `diora`.
- `[optional flags]`: please refer to [Optional flags](#optional-flags) for the options.

### Data

> **Note:** when passing the name to the grammar induction, leave out the `.txt` extension!

The messages used for inferring the grammars have to be in a text file (ending with `.txt`) in the `data/` directory.
The text files contain words/symbols separated by a single space, with one message per row. Please make sure that:
- there is no empty line in the data file containing the messages; and
- there is no punctuation.

For instance, the first few lines of a text file could look like this:

```
4 4 4 4 4
3 3 2 2 4
0 5 0 3 2
3 2 2 3
2 2 2 1 5
```

For inducing a grammar from an emergent language, you only need one text file (the induction set). However, you can also provide an evaluation set for the same language. Additionally, for inducing GloVe embeddings for the symbols and creating baselines you can have a file with all the messages. For instance, your `data/` directory could contain the following files:

```
├── data
│   ├── language.txt
│   ├── language_eval.txt
│   ├── language_full.txt
```

### Optional flags

The following optional flags are supported and should be put after the name of the parser (`ccl` or `diora`):
- `--eval=`: name of the .txt file in `data/` containing the evaluation set; e.g, `--eval=language_eval`.
- `--langfull=`: name of the .txt file in `data/` containing all the messages you want to use for creating the GloVe word embeddings; e.g. `--langfull=language_full`.
- `--analysis`: evaluates the resulting grammar(s) and appends the results to `results/analysis.csv`.
- `--struct_baseline`: create a structured baseline; also requires setting `-V` and `-L` (see below); example: `--struct_baseline`
- `--rand_baseline`: create a random baseline based on the emergent full or induct messages; example `--rand_baseline`
- `--shuf_baseline`: create a shuffled baseline based on the emergent full or induct messages; example: `--shuf_baseline`
- `-V=`: (required for `--struct_baseline`) vocabulary size for the structured baseline as integer; example: `-V=13`
- `-L=`: (required for `--struct_baseline` and `--overgen_num`) message length for the structured baseline as integer; example: `-L=10`
- `--overgen_num=`: number of samples for computing overgeneration coverage (default is 0); example: `--overgen_num=10`

### Grammar analysis

If the `--analysis` flag is provided, the resulting grammars are evaluated on various metrics. See the paper for an explanation of the metrics. The following metrics can be found in the resulting `analysis.csv` among the results:
- `name`: name of the original language.
- `parser`: constituency parser used (`ccl` or `diora`).
- `type`: either `emergent` for the tested emergent language, or `rand`, `shuf` or `struct` for the respective baselines.
- `date+timestamp`: timestamp for when the row of values is provided.
- `induct_fp`: file path of induction set.
- `eval_fp`: file path of evaluation set.
- `full_fp`: file path of used full set containing all messages.
- `log2prior`: GDL in paper; the size of the grammar.
- `terminals`: number of terminals.
- `preterminals`: number of preterminals.
- `recursive`: number of recursive rules.
- `avg terminals/preterminal`: average number of terminals per preterminal.
- `avg preterminals/terminal`: average number of preterminals per terminal.
- `eval_average_log2likelihood`: DDL on evaluation set.
- `induct_average_log2likelihood`: DDL on induction set.
- `induct_coverage`: coverage on induction set.
- `eval_coverage`: coverage on evaluation set.
- `overgeneration_coverage`: overgeneration coverage.
- `overgeneration_coverage_N`: number of random messages sampled for calculating the overgeneration coverage.
- `number of nominals`:
- `number of pre-terminal groups`:
- `average number of pre-terminal groups generated by nominal`: average number of pre-terminal groups generated by the same non-terminal.

## Examples

The following examples illustrate the use of `emergent_grammar_induction`, where we have three files with messages from the same emergent language:

```
├── data
│   ├── demo_language.txt       # the induction set
│   ├── demo_language_eval.txt  # a disjoint evaluation set
│   ├── demo_language_full.txt  # the full set (i.e. all the messages)
```

### CCL

Run CCL-BMM on the emergent language and three baselines (structured, shuffled, and random baseline with `V=13` and `L=10`).
Analyse the resulting grammars on several metrics, including the `overgeneration coverage` with 100 random samples.
All of the optional flags are used.

```
docker run --rm \
	-v $(pwd)/data:/usr/src/app/data \
	-v $(pwd)/results/:/usr/src/app/results/grammars \
	-v $(pwd)/logs:/usr/src/app/logs \
	oskarvanderwal/emergent-grammar-induction demo_language ccl \
	--eval=demo_language_eval \
	--langfull=demo_language_full \
	--analysis \
	--struct_baseline \
	--shuf_baseline \
	--rand_baseline \
	--overgen_num=100 \
	-V=13 \
	-L=10
```

### DIORA

Run DIORA-BMM on the emergent language and three baselines (structured, shuffled, and random baseline with `V=13` and `L=10`).
Analyse the resulting grammars on several metrics, but without the `overgeneration coverage`.

```
docker run --rm --gpus all \
	-v $(pwd)/data:/usr/src/app/data \
	-v $(pwd)/results/:/usr/src/app/results/grammars \
	-v $(pwd)/logs:/usr/src/app/logs \
	oskarvanderwal/emergent-grammar-induction:diora demo_language diora \
	--eval=demo_language_eval \
	--langfull=demo_language_full \
	--analysis \
	--struct_baseline \
	--shuf_baseline \
	--rand_baseline \
	-V=13 \
	-L=10
```

## Reproduce our paper

**TODO**

The emergent languages used in the paper can be found in `data/simple-referential-game/`.
Before starting the experiment, make sure your `results/` is empty or does not exist yet, because these files could be overwritten.

You can use `scripts/run_reproduce_paper.sh` for analysing these emergent languages:

```
bash scripts/run_reproduce_paper.sh data/simple-referential-game/ ccl # For using CCL as constituency parser
bash scripts/run_reproduce_paper.sh data/simple-referential-game/ diora # For using DIORA as constituency parser
```

The resulting grammars and analysis metrics can be found in `results/`. Specifically,
- the inferred grammars are in `results/{ccl,diora}` (depending on the used constituency parser);
- the structured baseline grammars are in `results/structured_grammar/`, the sampled messages in `emergent_dataset/`, and the reconstructed grammars can be found with the other induced grammars (the files ending with `__struct_baseline_induct.pcfg`);
- the results of the analysis is in `analysis.csv`.

## Build EGI yourself

Instead of using our [`emergent-grammar-induction`](https://hub.docker.com/r/oskarvanderwal/emergent-grammar-induction) images on the Docker Hub, you can build the images yourself using this repository and the Dockerfiles.

First, clone this repository, including the submodules (for including CCL, DIORA, BMM_labels, and GloVe):

```
git clone --recurse-submodules https://github.com/i-machine-think/emergent_grammar_induction.git
```

Now we can build the setup from the Dockerfile `ccl.Dockerfile` or `diora.Dockerfile`, and give it the name `emergent_grammar_induction` with the `-t` flag. Make sure to run this from the root directory of this repository where the `Dockerfile` lives:

```
docker build . -t emergent_grammar_induction -f ccl.Dockerfile # Smaller image with only ccl
docker build . -t emergent_grammar_induction -f diora.Dockerfile # Larger image with both ccl and diora
```

To test whether the build works correctly, you can run the induction on `demo_language.txt` with CCL as constituency parser that puts the resulting grammar in `results/`:

```
docker run --rm -v $(pwd)/results/:/usr/src/app/results/grammars emergent_grammar_induction
```

## Troubleshooting

In case you want to interrupt a running experiment, you can use `docker stop` with the Docker container name (if you have used the flag `--name`) or its ID:

```
docker stop <CONTAINER-ID/CONTAINER-NAME>
```

The IDs of all running experiments (Docker containers) can be found with:

```
docker ps
```
