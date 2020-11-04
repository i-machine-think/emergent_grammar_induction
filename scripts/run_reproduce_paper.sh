#!/bin/bash
#
# run_reproduce_paper.sh
#
# This script can be used for reproducing the results
# of the main experiments in the paper.
# Make sure you have the messages of the emergent languages
# in the directory `data/`.
# 
# ARGS
# ----
#
# argument 1    -   relative path to the data directory
#                   example 'data/' or '../data/'
# argument 2    -   indicating the constituency parser
#                   example: 'ccl' or 'diora'
#                   
# BEHAVIOUR
# ---------
#
# expected output  -  created files containing PCFGs to 'results/{ccl,diora}/'
# suggested usage  -  bash scripts/run_reproduce_paper.sh <relative path to directory> {ccl,diora}

umask 0000 # Ensures that the created files are not locked and can only be accessed with root permissions

function halt_experiments()
{
    # This function makes it easier to halt the running docker containers.
    printf "\nHalting experiments.\nStopping running container:\n"
    docker stop 'emergent_grammar_V'$v'L'$l
    exit
}

trap halt_experiments SIGINT

printf "Starting gramar induction and analysis for V {6,13,27} and L {3,5,10}.\n"
printf "Constituency parser used: $2.\n"
printf "Use CTRL+C to interrupt the experiments.\n\n"

for l in 3 5 10; do
    for v in 6 13 27; do
        for s in 0 1 2; do
            inductionset='V'$v'L'$l's'$s'_orig'
            evaluationset='V'$v'L'$l's'$s'_eval'
            fullset='V'$v'L'$l's'$s'_full'

            randomset='V'$v'L'$l'_rand'
            shuffleset='V'$v'L'$l'_shuf'

            echo "Running grammar induction and analysis on induction set $inductionset"

            # Induction set
            if [[ $2 = ccl ]]; then
                docker run --rm -d \
                --name 'emergent_grammar_V'$v'L'$l \
	            -v $(pwd)/$1:/usr/src/app/data \
	            -v $(pwd)/results/:/usr/src/app/results/grammars \
	            -v $(pwd)/logs:/usr/src/app/logs \
	            oskarvanderwal/emergent-grammar-induction $inductionset ccl \
	            --eval=$evaluationset \
	            --langfull=$fullset \
	            --analysis \
	            --struct_baseline \
	            --overgen_num=500 \
	            -V=$v \
	            -L=$l
            elif [[ $2 = diora ]]; then
                docker run --rm --gpus all -d \
                --name 'emergent_grammar_V'$v'L'$l \
	            -v $(pwd)/$1:/usr/src/app/data \
	            -v $(pwd)/results/:/usr/src/app/results/grammars \
	            -v $(pwd)/logs:/usr/src/app/logs \
	            oskarvanderwal/emergent-grammar-induction:diora $inductionset diora \
	            --eval=$evaluationset \
	            --langfull=$fullset \
	            --analysis \
	            --struct_baseline \
	            --overgen_num=500 \
	            -V=$v \
	            -L=$l
            fi

            status_code=$(docker container wait 'emergent_grammar_V'$v'L'$l)
            printf "Done.\n\n"
            printf "Running grammar induction and analysis on random baseline $randomset"
            
            # Random set
            if [[ $2 = ccl ]]; then
                docker run --rm \
                --name 'emergent_grammar_V'$v'L'$l -d \
	            -v $(pwd)/$1:/usr/src/app/data \
	            -v $(pwd)/results/:/usr/src/app/results/grammars \
	            -v $(pwd)/logs:/usr/src/app/logs \
	            oskarvanderwal/emergent-grammar-induction $randomset ccl \
	            --langfull=$fullset \
	            --analysis \
	            --overgen_num=500 \
	            -V=$v \
	            -L=$l
            elif [[ $2 = diora ]]; then
                docker run --rm --gpus all \
                --name 'emergent_grammar_V'$v'L'$l -d \
	            -v $(pwd)/$1:/usr/src/app/data \
	            -v $(pwd)/results/:/usr/src/app/results/grammars \
	            -v $(pwd)/logs:/usr/src/app/logs \
	            oskarvanderwal/emergent-grammar-induction:diora $randomset diora \
	            --langfull=$fullset \
	            --analysis \
	            --overgen_num=500 \
	            -V=$v \
	            -L=$l
            fi

            status_code=$(docker container wait 'emergent_grammar_V'$v'L'$l)
            printf "Done.\n\n"
            echo "Running grammar induction and analysis on shuffled baseline $shuffleset"
            
            # Shuffled set
            if [[ $2 = ccl ]]; then
                docker run --rm \
                --name 'emergent_grammar_V'$v'L'$l -d \
	            -v $(pwd)/$1:/usr/src/app/data \
	            -v $(pwd)/results/:/usr/src/app/results/grammars \
	            -v $(pwd)/logs:/usr/src/app/logs \
	            oskarvanderwal/emergent-grammar-induction $shuffleset ccl \
	            --langfull=$fullset \
	            --analysis \
	            --overgen_num=500 \
	            -V=$v \
	            -L=$l
            elif [[ $2 = diora ]]; then
                docker run --rm --gpus all \
                --name 'emergent_grammar_V'$v'L'$l -d \
	            -v $(pwd)/$1:/usr/src/app/data \
	            -v $(pwd)/results/:/usr/src/app/results/grammars \
	            -v $(pwd)/logs:/usr/src/app/logs \
	            oskarvanderwal/emergent-grammar-induction:diora $shuffleset diora \
	            --langfull=$fullset \
	            --analysis \
	            --overgen_num=500 \
	            -V=$v \
	            -L=$l
            fi

            status_code=$(docker container wait 'emergent_grammar_V'$v'L'$l)
            printf "Done.\n\n"
        done
    done
done
