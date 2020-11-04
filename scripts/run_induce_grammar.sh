#!/bin/bash

# run_induce_grammar.sh
#
# This script runs the two-stage grammar induction, either CCL+BMM or DIORA+BMM
#
# ARGS
# ----
#
# argument 1       -  name of the input file without extension
#                     example: 'demo_language'
# argument 2       -  indicating the constituency parser
#                     example: 'ccl' or 'diora'
# FLAGS
# -----
#
# --langfull       -  (optional) name of full message set without .txt
#                  -  example: --langfull=demo_language_full
# --eval           -  (optional) name of evaluation message set without .txt
#                  -  example: --eval=demo_language_eval
# --struct_baseline-  (optional) create a structured baseline; also requires setting -V and -L
#                     example: --struct_baseline -V=13 -L=10
# --rand_baseline  -  (optional) create a random baseline based on the emergent full or induct messages
#                     example: --rand_baseline
# --shuf_baseline  -  (optional) create a shuffled baseline based on the emergent full or induct messages
#                     example: --shuf_baseline
# -V               -  (required for --struct_baseline) vocabulary size for struct baseline as integer
#                     example: -V=13
# -L               -  (required for --struct_baseline and --overgen_num) message length for struct baseline as integer
#                     example: -L=10
# --overgen_num    -  (optional) number of random samples for estimating the overgeneration coverage
#                     example: --overgen_num=10 -L=10
#
# BEHAVIOUR
# ---------
#
# expected output  -  created file containing PCFG to 'results/grammars/'
#                     example output: 'demo_language.pcfg'
# suggested usage  -  bash run_induce_grammar.sh <filename>

umask 0000 # Ensures that the created files are not locked and can only be accessed with root permissions

#echo $(ls data)

# Default values
CONST=$2
LANGFULL="$1"
EVAL="$1"
ANALYSIS=false
STRUCT_BASELINE=false
RAND_BASELINE=false
SHUF_BASELINE=false
VOCAB_SIZE=false
MESSAGE_LENGTH=false
SETSIZE=false
LANGUAGE_DIR=false
LOGDIR=logs/"$(date +"%d-%m-%Y__%H-%M-%S")"
NUM_OVERGENERATION_SAMPLES=0 # number of random message samples for overgeneration coverage
DATADIR='data'

# Read flags
for i in "$@"
do
    case $i in
	--langfull=*)
	    LANGFULL="${i#*=}" # The file with all messages of the language
	    ;;
	--eval=*)
	    EVAL="${i#*=}" # The file with the evaluation messages of the language
	    ;;
	--analysis)
	    ANALYSIS=true
	    ;;
	--struct_baseline)
	    STRUCT_BASELINE=true
	    ;;
	--rand_baseline)
	    RAND_BASELINE=true
	    ;;
	--shuf_baseline)
	    SHUF_BASELINE=true
	    ;;
    --overgen_num=*)
        NUM_OVERGENERATION_SAMPLES="${i#*=}"
        ;;
	-V=*)
	    VOCAB_SIZE="${i#*=}"
	    ;;
	-L=*)
	    MESSAGE_LENGTH="${i#*=}"
	    ;;
	*)
            # unknown option
	    ;;
    esac
done

# Create log directory
mkdir $LOGDIR
echo "Log files can be found in $LOGDIR"

# Check if files exist
if [ ! -f "$DATADIR/$1.txt" ]; then
    if [[ $SETSIZE != true ]]; then
        echo "Error: File $1.txt not found in $DATADIR!"
        exit 1
    fi
fi

if [ ! -f "$DATADIR/$EVAL.txt" ]; then
    if [[ $SETSIZE != true ]]; then
        echo "Error: File $EVAL.txt not found in $DATADIR!"
        exit 1
    fi
fi

if [ ! -f "$DATADIR/$LANGFULL.txt" ]; then
    if [[ $SETSIZE != true ]]; then
        echo "Error: File $LANGFULL.txt not found in $DATADIR!"
        exit 1
    fi
fi

# Run Glove to get word embedding vectors
function glove {
    mkdir -p results/glove
    bash scripts/run_glove.sh --corpus="$DATADIR/$1.txt" --glove="pipeline/glove" --output="results/glove" --name=$1 > $LOGDIR/glove.log #| tee $LOG_DIR/"$INPUT"_glove.log
}

# Run CCL parser
function ccl {
    # arg1 : name message set
    mkdir -p results/ccl
    # Prepare CCL exec file
    echo "pipeline/ccl/corpus.txt line learn" > pipeline/ccl/exec_file
    echo "pipeline/ccl/corpus.txt line parse -o results/ccl/$1 -s ccl" >> pipeline/ccl/exec_file
    
    # Run CCL using instructions exec file
    pipeline/ccl/cclparser pipeline/ccl/exec_file > $LOGDIR/$1_ccl.log 2>&1
    
    # Prepare input file for BMM
    cat pipeline/ccl/corpus.txt | awk '{print $0" ."}' > "results/bmm/$1.txt"
    
    # Convert constituents to BMM readable format
    python utils/convert2constituents.py --bracket_file results/ccl/$1.ccl --format ccl --shapes True --output "results/bmm/$1"
}

# Run DIORA parser
function diora {
    # arg1 : name message set
    # arg2 : name glove vector set
    mkdir -p results/diora
    GLOVE_DIORA=$PWD/results/glove/vectors$2.txt
    DIORA_DIR_DIORA=$PWD/pipeline/diora
    CORPUS_DIORA=$PWD/pipeline/ccl/corpus.txt
    NUM_MESSAGES=$(cat $CORPUS_DIORA | wc -l)
    # Take the minimum value to make sure batch_size is not larger than the whole message set
    BATCH_SIZE=$(( $NUM_MESSAGES < 128 ? $NUM_MESSAGES : 128 ))
    EPOCHS=5
    CUDA="--cuda --multigpu" # set "--cuda" if using CUDA and "" if not
    LOG_DIORA=$PWD/$LOG_DIR/$1_diora.log
    
    (cd pipeline/diora/pytorch;
     export PYTHONPATH=$(pwd):$PYTHONPATH;

     echo "Training DIORA model..."
     python diora/scripts/train.py --data_type txt --emb w2v --embeddings_path $GLOVE_DIORA --train_path $CORPUS_DIORA --validation_path $CORPUS_DIORA --save_latest 1 --save_after 0 --experiment_path $DIORA_DIR_DIORA --max_epoch $EPOCHS $CUDA --batch_size $BATCH_SIZE --log_every_batch 1 | tee $LOG_DIORA;

     echo "Parse trees with trained diora model"
     python diora/scripts/parse.py --data_type txt --embeddings_path glove/vectors.txt load_model_path output/model_periodic.pt python diora/scripts/parse.py --data_type txt --embeddings_path $GLOVE_DIORA --load_model_path $DIORA_DIR_DIORA/model_periodic.pt $CUDA --validation_path $CORPUS_DIORA --experiment_path "$DIORA_DIR_DIORA" > $LOG_DIORA #> $DIORA_DIR_DIORA/parse_trees_$1.txt
    )
    python utils/convert2constituents.py --bracket_file "$DIORA_DIR_DIORA/parse.jsonl" --format diora --shapes True --output "results/bmm/$1"
}

# Run BMM grammar induction
function bmm {
    # arg1 : name message set
    mkdir -p results/bmm/Output
    (
    cd results/bmm
    java -jar -Xmx4096m -Xms2048m ../../pipeline/bmm/BMM.jar "$1.txt" "$1.span" > ../../$LOGDIR/$1_bmm.log
    )
}

function grammar_induction {
    # arg1 : name emergent
    # arg2 : type (e.g. emergent, shuf, rand, struct)
    # arg3 : name induct text file (excluding .txt)
    # arg4 : name full text file (excluding .txt)
    # arg5 : name eval text file (excluding .txt)
    # arg6 : message length of messages

    echo ""
    echo "Inducing grammar using $3"
    
    # Copy data file containing messages to corpus.txt
    # Start with new corpus for CCL
    [ ! -e pipeline/ccl/corpus.txt ] || rm pipeline/ccl/corpus.txt
    cat "$DATADIR/$3.txt" >> pipeline/ccl/corpus.txt
    ed -s ccl/corpus.txt <<< w # append newline character if not already present

    mkdir -p results/bmm

    if [[ $CONST = ccl ]]; then
	    echo "CCL running"
	    ccl $3
    elif [[ $CONST = diora ]]; then
        echo "GloVe and diora running"
        glove $4
        diora $3 $4
    fi

    # Run BMM
    echo "BMM running"
    bmm $3

    # Parse BMM output to clean PCFG
    mkdir -p results/grammars/$CONST
    python utils/bmm_labels2grammar.py --grammar results/bmm/Output/Induced_Grammar.txt --output results/grammars/$CONST/$3.pcfg

    ###########
    # Analysis
    ###########
    if [[ $ANALYSIS != false ]]; then
	    echo "Providing metrics for the induced grammar"
        
        if [[ $MESSAGE_LENGTH != false ]]; then
	        python utils/analysis.py --parser $CONST --grammar "results/grammars/$CONST/$3.pcfg" --name "$1" --type "$2" --induct "$DATADIR/$3.txt" --eval "$DATADIR/$5.txt" --full "$DATADIR/$4.txt" --output results/grammars/analysis.csv -L "$MESSAGE_LENGTH" --overgeneration "$NUM_OVERGENERATION_SAMPLES" --log_dir $LOGDIR
        else
            python utils/analysis.py --parser $CONST --grammar "results/grammars/$CONST/$3.pcfg" --name "$1" --type "$2" --induct "$DATADIR/$3.txt" --eval "$DATADIR/$5.txt" --full "$DATADIR/$4.txt" --output results/grammars/analysis.csv --log_dir $LOGDIR
        fi
    fi
}


# Run grammar induction
grammar_induction $1 "emergent" $1 $LANGFULL $EVAL

# Create baseline messages if called for

if [[ $STRUCT_BASELINE == true ]]; then
    NAME="$1__struct_baseline"
    echo "creating $NAME"
    python utils/baselines.py --baseline struct -V $VOCAB_SIZE -L $MESSAGE_LENGTH  --name $NAME
    grammar_induction $1 "struct" "$NAME"_induct "$NAME"_full "$NAME"_eval
fi

if [[ $RAND_BASELINE == true ]]; then
    NAME="$1__rand_baseline"
    echo "creating $NAME"
    python utils/baselines.py --baseline rand --emergent "$DATADIR/$LANGFULL.txt" --name $NAME
    grammar_induction $1 "rand" "$NAME"_induct "$NAME"_full "$NAME"_eval
fi

if [[ $SHUF_BASELINE == true ]]; then
    NAME="$1__shuf_baseline"
    echo "creating $NAME"
    python utils/baselines.py --baseline shuf --emergent "$DATADIR/$LANGFULL.txt" --name $NAME
    grammar_induction $1 "shuf" "$NAME"_induct "$NAME"_full "$NAME"_eval
fi

echo 'Grammar induction procedure is finished'
