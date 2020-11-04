from nltk import PCFG, CFG, Nonterminal
from nltk.parse.viterbi import ViterbiParser
from nltk.draw.tree import TreeView
import nltk
from itertools import count
import re
import argparse
import os

'''
This script reads the grammar output from BMM labels and converts it
to NLTKs PCFG.
See https://www.nltk.org/_modules/nltk/grammar.html for useful documentation for PCFG
'''

# Necessary to also recognise numbers such as 1e-5
# original: nltk.grammar_PROBABILITY_RE = re.compile(r'( \[ [\d\.]+ \] ) \s*', re.VERBOSE)
nltk.grammar._PROBABILITY_RE = re.compile(r'( \[([\d\.]+)(e-\d*)?\] ) \s*', re.VERBOSE)

TERMINALS = []

def parse_induced_grammar(filepath):
    ''' Return string with grammar in format NLTK PCFG can read
    See: https://www.nltk.org/howto/grammar.html '''
    with open(filepath, 'r') as f:
        lines = f.readlines()

    non_terminals = []
    flag_skip = True
    newline = ""
    string = ""
    left = ""
    right = []
    nonTFlag = False
    for line in lines:
        if flag_skip:
            # Skip first few lines
            if "PRODUCTION RULES" in line:
                # simplify non-terminals to letter pairs
                wordid = dict(zip(set(non_terminals), count(1)))
                alphabet = [chr(i) for i in range(ord('A'),ord('Z')+1)] + [chr(i) for i in range(ord('a'),ord('z')+1)] # List of letters
                alphabet2 = [i+j for i in alphabet for j in alphabet]
                alphabet = alphabet + alphabet2 + [i+j for i in alphabet2 for j in alphabet]
                
                dictionary = dict(zip(wordid, alphabet[:len(wordid)]))
                flag_skip = False
                continue
            if nonTFlag:
                line = line.rstrip()
                if not "TOP" in line:
                    non_terminals.append(line)
            if "NONTERMINALS" in line:
                nonTFlag = True
            continue
        
        if "RULESOFNONTERMINAL" in line.split()[0]:
            if right:
                string += newline + left + " -> " + " | ".join(right)
                newline = "\n"
            left = line.split()[1]
            if left in dictionary:
                left = dictionary[left]
            right = []
        else:
            term_list = line.split("*#")[0]
            terms = []
            for term in term_list.split("*"):
                if term in dictionary:
                    term = dictionary[term]
                elif term.isdigit() or (not term in non_terminals) or (not "TOP" in term): # To have it accept as a terminal
                    term = f"'{term}'"
                    TERMINALS.append(term) # Used for testing the PCFG
                terms.append(term)
            terms = " ".join(terms)
            probability = line.split("*#")[1].rstrip()

            right.append(f"{terms} [{float(probability.lower())}]")
            
    string += newline + left + " -> " + " | ".join(right)
    return string

def test_PCFG(grammar, shapes=False):
    ''' Test whether the grammar can parse a sentence '''
    #sent = [i.replace("'","") for i in TERMINALS[:5]]
    #sent = "in the middle center is a green square".split()
    if not shapes:
        sent = "2 2 2 12 2 12 2 2 12 2".split()
    else:
        sent = "in the middle center is a green square".split()
    sr = ViterbiParser(grammar)
    for t in sr.parse(sent):
        t.draw()

def main(config):
    grammar_string = parse_induced_grammar( config.grammar )

    if config.output:
        with open(config.output, 'w') as f:
            f.write(grammar_string)
    grammar = PCFG.fromstring( grammar_string )
    grammar._start = Nonterminal('TOP') # Not sure whether this is allowed or breaks things

    # Create directory for parse_trees if it does not already exist
    if config.textfile:
        if not os.path.exists(config.output_parse):
            os.makedirs(config.output_parse)
    
    if config.textfile:
        parser = ViterbiParser(grammar)
        with open(config.textfile, 'r') as f:
            lines = f.read().splitlines() 
        for i, line in enumerate(lines):
            if i==config.number_parses:
                break
            print(f"Parsing sentence {i+1}")
            sent = line.split()
            for t in parser.parse(sent):
                TreeView(t)._cframe.print_to_file(f"{config.output_parse}/tree_{i}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--grammar', '-g', type=str, required=True, help="Path to Induced Grammar.")
    parser.add_argument('--output', '-o', type=str, default=None, help="Save grammar to this file path.")
    parser.add_argument('--textfile', type=str, default=None, help="Optional textfile to parse with the grammar.")
    parser.add_argument('--output_parse', type=str, default="parse_trees", help="Where to put the parse trees if parsing sentences.")
    parser.add_argument('--number_parses', type=int, default=10, help="Maximum number of lines to parse the corpus.")
    config = parser.parse_args()
    main(config)
