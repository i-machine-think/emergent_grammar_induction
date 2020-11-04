import argparse
import numpy as np
import nltk
from nltk import PCFG, Nonterminal
from nltk.parse.viterbi import ViterbiParser
import statistics
import random
import csv
import os
import re
from datetime import datetime
import logging

parser = argparse.ArgumentParser()
parser.add_argument('--grammar', type=str, required=True,
                    help="Path to file containing a PCFG")
parser.add_argument('--name', type=str, required=True,
                    help="Name of emergent message set")
parser.add_argument('--type', type=str, required=True,
                    help="Type (e.g. emergent, shuf, rand, struct)")
parser.add_argument('--parser', type=str, required=True,
                    help="Name of the used constituency parser")
parser.add_argument('--induct', type=str, required=True,
                    help="Path to file containing induction messages")
parser.add_argument('--eval', type=str, required=True,
                    help="Path to file containing evaluation messages")
parser.add_argument('--full', type=str, required=True,
                    help="Path to file containing all messages")
parser.add_argument('--output', type=str, required=True,
                    help="Path to output csv file with metrics")
parser.add_argument('-L', type=int, required=False,
                    help="Fixed message length of the language (required for overgeneration coverage).")
parser.add_argument('--overgeneration', type=int, default=0,
                    help="Testing overgeneration coverage with this number of samples (requires setting -L).")
parser.add_argument('--log_dir', type=str, required=False,
                    help="The directory for storing the log file.")

# Necessary to also recognise numbers such as 1e-5
# original: nltk.grammar_PROBABILITY_RE = re.compile(r'( \[ [\d\.]+ \] ) \s*', re.VERBOSE)
nltk.grammar._PROBABILITY_RE = re.compile(r'( \[([\d\.]+)(e-\d*)?\] ) \s*', re.VERBOSE)

def get_terminals(pcfg):
    """Returns a list of all the terminals in the PCFG."""
    prods_lexical = [prod for prod in pcfg.productions() if type(prod.rhs()[0]) == str]
    preterminals = {}
    terminals = {}
    for prod in prods_lexical:
        pt = str(prod.lhs())
        symbol = list(prod.rhs())
        # preterminals
        if pt not in preterminals:
            preterminals[pt] = symbol
        else:
            preterminals[pt] = preterminals[pt] + symbol

        # terminals
        symbol = ''.join(symbol)
        if symbol not in terminals:
            terminals[symbol] = [pt]
        else:
            terminals[symbol] = terminals[symbol] + [pt]
    return list(terminals.keys())

def sample_message(L,vocabulary):
    """
    Sample message from the whole space of size |vocabulary|^L.
    """
    message = []
    for i in range(0,L):
        message.append(random.choice(vocabulary))
    return message

def overgeneration_coverage(pcfg, L, num_samples):
    """
    Test the overgeneration coverage with num_samples random messages with message length L.
    Returns % of successfull parses.
    """
    parser = ViterbiParser(pcfg)
    
    parse_total = 0 # Total number of messages tried to parse
    parse_success = 0 # Total number successfully parsed


    # Get the random messages
    vocabulary = get_terminals(pcfg)
    for i in range(0,num_samples):
        message = sample_message(L,vocabulary)
        parse_total += 1
        try:
            if parser.parse_one(message):
                parse_success += 1
        except ValueError:
            continue
    return parse_success/parse_total*100
    

def analyse_grammar(pcfg):
    """
    Analyses the properties of the grammar.
    Returns a dictionary for summarized properties
    """

    top_nonterminal = nltk.grammar.Nonterminal('TOP')
    prods_top =        [prod for prod in pcfg.productions() if prod.lhs() == top_nonterminal]
    prods_lexical =    [prod for prod in pcfg.productions() if type(prod.rhs()[0]) == str]
    prods_nonlexical = [prod for prod in pcfg.productions() if prod not in prods_top + prods_lexical]
    nonterminals = set([nonterm for prod in prods_nonlexical+prods_top for nonterm in prod.rhs()])
    terminals    = set([prod.rhs()[0] for prod in prods_lexical])
    nonterminal_count = len(nonterminals)
    terminal_count    = len(terminals)
    preterminal_count = len(set(prod.lhs() for prod in prods_lexical))
    binary_rule_count    = len([prod for prod in pcfg.productions() if len(prod.rhs()) == 2])
    unary_rule_count     = len([prod for prod in prods_nonlexical + prods_top if len(prod.rhs()) == 1])
    recursive_rule_count = len([prod for prod in pcfg.productions() if prod.lhs() in prod.rhs()]) # RHS contains LHS

    # Computing model prior
    GDL_top = np.log2(nonterminal_count + 1) * sum(len(prod.rhs())+1 for prod in prods_top)
    GDL_lex = (np.log2(nonterminal_count + 1) + np.log2(terminal_count)) * terminal_count
    GDL_non = np.log2(nonterminal_count + 1) * sum(len(prod.rhs())+1 for prod in prods_nonlexical)
    GDL_sep = np.log2(nonterminal_count + 1) * 2

    log_prior = (GDL_top + GDL_lex + GDL_non + GDL_sep)

    # Collect results in dict
    grammar_stats = {
        'prods': len(pcfg.productions()),
        'prods_top': len(prods_top),
        'prods_lexical': len(prods_lexical),
        'prods_nonlexical': len(prods_nonlexical),
        'terminals': terminal_count,
        'nonterminals': nonterminal_count,
        'preterminals': preterminal_count,
        'unary': unary_rule_count,
        'binary': binary_rule_count,
        'recursive': recursive_rule_count,
        'prods_top_dl': GDL_top,
        'prods_lexical_dl': GDL_lex,
        'prods_nonlexical_dl': GDL_non,
        'log2prior': log_prior
    }
    return grammar_stats

def get_stat_dicts(pcfg):
    """
    Returns dictionaries with a list of pre-terminals/terminals 
    a terminal/pre-terminal points to.
    E.g. A --> [1, 2, 3] and 1 --> [A, B, C]
    """
    prods_lexical = [prod for prod in pcfg.productions() if type(prod.rhs()[0]) == str]
    preterminals = {}
    terminals = {}
    for prod in prods_lexical:
        pt = str(prod.lhs())
        symbol = list(prod.rhs())
        
        # preterminals
        if pt not in preterminals:
            preterminals[pt] = symbol
        else:
            preterminals[pt] = preterminals[pt] + symbol

        # terminals
        if symbol[0] not in terminals:
            terminals[symbol[0]] = list(pt)
        else:
            terminals[symbol[0]] = terminals[symbol[0]] + list(pt)
    return preterminals, terminals

def prod_check_in_RHS(production, preterminals, terminals):
    """Check if prod.rhs() is a subset of l"""
    RHS = [str(p) for p in production.rhs()]
    return (set(RHS) <= (set(preterminals)|set(terminals))) and len(RHS)>1

def get_wordclass_combinations(pcfg, preterminals, terminals):
    """Get all combinations of two pre-terminals"""
    preterminals = list(preterminals.keys())
    # Check for productions with only pre-terminals on the RHS
    prods_nominal_groups = [prod for prod in pcfg.productions() if prod_check_in_RHS(prod, preterminals, terminals)]
    return prods_nominal_groups

def get_stats_wordclass_groups(pcfg, preterminals, terminals):
    """Returns for a PCFG and a list of preterminals and terminals,
    the unique number of pre-terminal group generating non-terminals (LHS)
    and unique number of pre-terminal groups (RHS)
    as well as the average number of repeating LHS and RHS"""
    prods = get_wordclass_combinations(pcfg, preterminals, terminals)
    LHS = {}
    RHS = {}
    LHS_count = {}
    RHS_count = {}
    for prod in prods:
        left = str(prod.lhs())
        right = tuple([str(i) for i in prod.rhs()])

        if left not in LHS:
            LHS[left] = [right]
            LHS_count[left] = 1
        else:
            LHS[left] = LHS[left] + [right]
            LHS_count[left] = LHS_count[left] + 1

        if right not in RHS:
            RHS[right] = [left]
            RHS_count[right] = 1
        else:
            RHS[right] = RHS[right] + [left]
            RHS_count[right] = RHS_count[right] + 1

    avg_LHS_count = statistics.mean(list(LHS_count.values()))
    avg_RHS_count = statistics.mean(list(RHS_count.values()))
    return LHS, RHS, avg_LHS_count, avg_RHS_count

def calculate_average(dictionary):
    """
    Calculates the average number of values in a list a key points to.
    """
    total = 0
    n = 0
    for k,v in dictionary.items():
        n += 1
        total += len(v)
    return total/n

def tree_depth(tree):
    '''
    Recursively computes depth of tree
    '''
    if type(tree[0]) == str:
        return 0
    else:
        return 1 + max(tree_depth(t) for t in tree)

def to_parse_string(tree):
    """
    Converts ProbabilisticTree to a one-line parse string with log-prob
    """
    if type(tree) == str: # symbol
        return tree
    else: #ProbabilisticTree
        return "({} {})".format(
            tree.label(),
            " ".join(to_parse_string(t) for t in list(tree))
        )

def ignore_none(l):
    """
    Removes None values from list
    """
    return [x for x in l if x is not None]

def mean(l):
    l = ignore_none(l)
    if l:
        return sum(l) / float(len(l))
    else:
        return None

def analyse_viterbi(pcfg, messages):
        """
        Infers the Viterbi parses of the fixed induction set, split induction set and evaluation set
        Writes parses to txt file
        Computes message likelihood, tree diversity and evaluation coverage
        Writes these properties to a pickle file
        Returns a list of strings for summarized properties
        """
        
        # Get terminals
        prods_lexical =    [prod for prod in pcfg.productions() if type(prod.rhs()[0]) == str]
        terminals    = set([prod.rhs()[0] for prod in prods_lexical])
        
        # Compute message likelihoods and tree depth
        parser = ViterbiParser(pcfg)
        message_count = len(messages)
        message_count_quarter = int(np.ceil(message_count/4))
        lines_parse = []
        trees = []
        tree_depths = []
        logprobs = []
        failed_parses = []
        parsed_count_weighted = 0
        for i, sent in enumerate(messages):
            sent = list(sent)
            if all(sym in terminals for sym in sent):
                tree_list = list(parser.parse(sent))
                if len(tree_list) == 1: # if the message can be parsed, tree_list contains one tree
                    tree = tree_list[0]
                    parse = to_parse_string(tree)
                    trees.append(parse)
                    tree_depths.append(tree_depth(tree))
                    logprobs.append(tree.logprob() / np.log(2)) # convert natural logarithm from tree to log base 2 for description length
                else:
                    parse = "NO_PARSE"
                    logprobs.append(None)
                    tree_depths.append(None)
                    failed_parses.append(sent)
            else:
                parse = "NO_PARSE"
                logprobs.append(None)
                tree_depths.append(None)
                failed_parses.append(sent)

        # Compute final statistics
        parsed_count = len(ignore_none(logprobs))
        unparsed_count = message_count - parsed_count

        # Collect evaluation information (of unique messages)
        eval_stats = {
            'log2likelihoods': logprobs, # corresponds to {data: frequencies}
            'unparsed_count': unparsed_count,
            'parsed_count': parsed_count,
            'failedparses': failed_parses,
        }
            
        # Evaluation coverage
        coverage = parsed_count / len(messages)
        eval_stats['coverage'] = coverage*100
        eval_stats['average_log2likelihood'] = mean(logprobs) or float('nan')
        
        return eval_stats

def load_messages(filename):
    """Helper function for loading the messages from a file"""
    with open(filename, 'r') as f:
        data = f.readlines()
        data = [tuple(line.split()) for line in data]
    return data

def main(args):
    logging.info("Reading and preparing grammar from file")
    # Read and prepare the grammar from file
    with open(args.grammar, 'r') as f:
        pcfg_string = f.read()
    induced_grammar = PCFG.fromstring(pcfg_string)
    induced_grammar._start = Nonterminal('TOP')

    logging.info("Reading and preparing induction and evaluation messages")
    # Read and prepare induction/evaluation messages
    induction_messages = load_messages(args.induct)
    evaluation_messages = load_messages(args.eval)

    # Get some metrics
    logging.info("Providing grammar related statistics")
    ## Grammar
    grammar_results = analyse_grammar(induced_grammar)

    logging.info("Providing word class statistics")
    ## Word classes
    preterminals, terminals = get_stat_dicts(induced_grammar)
    word_class_results = {
        'avg terminals/preterminal' : calculate_average(preterminals),
        'avg preterminals/terminal' : calculate_average(terminals),
    }

    ## Parses
    logging.info("Providing Viterbi parse related statistics")
    induct_viterbi_results = analyse_viterbi(induced_grammar, induction_messages)
    eval_viterbi_results = analyse_viterbi(induced_grammar, evaluation_messages)

    # Write to file
    args.output
    
    cols = ['name', 'parser', 'type', 'date+timestamp', 'induct_fp', 'eval_fp', 'full_fp']
    vals = [args.name, args.parser, args.type, datetime.now(), args.induct, args.eval, args.full]

    ## Add grammar metrics
    grammar_metrics = ['log2prior', 'terminals', 'preterminals', 'recursive']
    #grammar_metrics = ['GDL', 'terminals', 'preterminals', 'recursive']
    cols += grammar_metrics
    for m in grammar_metrics:
        vals.append(grammar_results[m])

    ## Add word class metrics
    word_class_metrics = ['avg terminals/preterminal', 'avg preterminals/terminal']
    cols += word_class_metrics
    for m in word_class_metrics:
        vals.append(word_class_results[m])
    
    ## Add parse metrics
    parse_metrics = ['average_log2likelihood', 'coverage']
    #parse_metrics = ['average_DDL', 'coverage']
    for m in parse_metrics:
        cols.append('induct_'+m)
        vals.append(induct_viterbi_results[m])
        cols.append('eval_'+m)
        vals.append(eval_viterbi_results[m])
    logging.debug(str(eval_viterbi_results['average_log2likelihood']))

    ## Add overgeneration coverage if -L and --overgeneration is set
    overgeneration_metrics = ['overgeneration_coverage','overgeneration_coverage_N']
    cols += overgeneration_metrics
    if (args.overgeneration>0) and args.L:
        logging.info("Estimating overgeneration coverage")
        vals.append(overgeneration_coverage(induced_grammar, args.L, args.overgeneration))
    else:
        logging.info("Skipping estimation of overgeneration coverage")
        vals.append('NaN')
    vals.append(args.overgeneration)

    ## Add preterminal group metrics
    logging.info("Calculating preterminal group metrics")
    preterminals, terminals = get_stat_dicts(induced_grammar)
    nominals, groups, nominals_count, groups_count = get_stats_wordclass_groups(induced_grammar, preterminals, terminals)
    preterminalgroup_metrics = ['number of nominals', 'number of pre-terminal groups', 'average number of pre-terminal groups generated by nominal']
    cols += preterminalgroup_metrics
    vals.append(len(nominals))
    vals.append(len(groups))
    vals.append(nominals_count)
    
    ## To csv file
    if not os.path.exists(args.output):
        with open(args.output, 'w') as f:
            writer = csv.writer(f)
            writer.writerows([cols]+[vals])
    else:
        with open(args.output, 'a') as f:
            writer = csv.writer(f)
            writer.writerows([vals])
    logging.info("Finished providing metrics for induced grammar")
    
if __name__ == "__main__":  
    args = parser.parse_args()
    if args.log_dir:
        logging.basicConfig(filename=args.log_dir+f"/{args.name}_grammar-analysis.log",
                            filemode='a',
                            format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                            datefmt='%H:%M:%S',
                            level=logging.DEBUG)
    logging.info(f"Starting analysis of grammar {args.name} of type {args.type} and constituency parser {args.parser}")
    main(args)
