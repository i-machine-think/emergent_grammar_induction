import numpy as np
import pickle
import argparse
import os
import re
from nltk import Tree, ParentedTree
from pprint import pprint
import ast

'''
This script is used for parsing the output constituency files of the CCL parser
and writes to a file which can be read by BMM_labels.
'''

def main(config):
    # Parse the constituency trees of CCL to strings on one line
    if config.format=='ccl':
        trees = parse2list_ccl(config.bracket_file, config.shapes)
    elif config.format=='diora':
        trees = parse2list_diora(config.bracket_file, config.shapes)
        text = parse2text_diora(config.bracket_file)
    lines = []
    # Go over each tree
    for t in trees:
        message = find_message(t, config.shapes)

        line = []
        # Read the string to an NLTK tree with the words swapped for indices
        tree = replace_terminals_with_indices(t)
        # Go over each sub tree and find the min and max index
        # to find a constituent
        for subtree in tree.subtrees():
            idx = [int(x) for x in subtree.leaves()]
            if idx:
                line.append( f"{min(idx)}-{max(idx)+1}")
        lines.append((message, " ".join(list(set(line)))))
    # Write the found constituent labels to a file
    newline = ""
    for i, line in enumerate(lines):
        if not config.shapes:
            with open(f"{config.output}.txt",'a+') as f:
                f.write(newline+line[0])
        elif config.format=='diora':
            with open(f"{config.output}.txt",'a+') as f:
                f.write(newline+text[i])
        with open(f"{config.output}.span",'a+') as f:
            span = remove_redundant_brackets( line[1] )
            f.write(newline+span)
        newline = "\n"

def remove_redundant_brackets(span):
    ''' Removes the bracketing in the tree for 0-1 ... (n-1)-n once.
    Because extra brackets were added to read the tree properly in NLTK,
    these brackets need to be removed again '''
    result = [e for e in re.split("[^0-9]", span) if e != '']
    max_int =  max(map(int, result))
    span = span.split()
    newspan = []
    ranges = [f"{i}-{i+1}" for i in range(0,max_int)]
    for j in span:
        if j in ranges:
            ranges.remove(j)
            continue
        else:
            newspan.append(j)
    return " ".join(newspan)

def replace_terminals_with_indices(treestring):
    ''' Replaces each terminal in the tree read from a string with an index in the sentence '''
    tree = ParentedTree.fromstring(treestring)
    for idx, _ in enumerate(tree.leaves()):
        tree_location = tree.leaf_treeposition(idx)
        non_terminal = tree[tree_location[:-1]]
        non_terminal[0] = str(idx)
    return tree
    
def find_message(tree, shapes=False):
    ''' Find the message in plain text from the tree '''
    if not shapes:
        return " ".join(re.findall(r'\d+', tree))+" ."
    else:
        return " ".join(re.findall(r'[^\s\(\)]+', tree))+" ."

def give_brackets(match):
    ''' Give an extra bracketing for each terminal and a label
    to avoid problems with parsing the string with NLTK '''
    return f"(L {match.group(0)})"

def flatten(container):
    ''' Flatten a list '''
    for i in container:
        if isinstance(i, (list,tuple)):
            for j in flatten(i):
                yield j
        else:
            yield i

def parse2text_diora(parse_path):
    ''' Parse diora output to text '''
    with open(parse_path, 'r') as p:
        lines = p.readlines()
    #lines = lines[1:] # Remove first line
    trees = []
    for line in lines:
        dictionary = ast.literal_eval(line)
        tree = dictionary["tree"]
        tree = " ".join( list(flatten(tree))+[" ."] )
        trees.append(tree)
    return trees

def parse2list_diora(parse_path, shapes):
    ''' Parse diora output to one tree string per line '''
    with open(parse_path, 'r') as p:
        lines = p.readlines()
    #lines = lines[1:] # Remove first line
    trees = []
    for line in lines:
        dictionary = ast.literal_eval(line)
        tree = str(dictionary["tree"])
        tree = tree.replace("[","(")
        tree = tree.replace("]",")")
        tree = tree.replace(',', '')
        tree = re.sub(r'[^\s\(\)]+', give_brackets, tree)
        trees.append(tree)
    return trees

def parse2list_ccl(parse_path, shapes=False):
    ''' Parse CCL output to one tree string per line '''
    with open(parse_path, 'r') as p:
        lines = p.readlines()

    # Put each tree in the list
    trees = []
    tree = ""
    bracket_sum=0

    # We know a new sentence has started when the left and right brackets
    # cancel each other out
    for line in lines:
        tree += line
        
        bracket_sum += line.count("(")+1
        bracket_sum -= line.count(")")+1

        if bracket_sum==0:
            tree = ' '.join(tree.split())
            tree = tree.replace("( ","(")
            tree = tree.replace(" )",")")
            tree = tree.replace(" (","(")
            tree = tree.replace(") ",")")
            if not tree=='':
                if not shapes:
                    tree = re.sub(r'[^\s\(\)]+', give_brackets, tree)
                else:
                    tree = re.sub(r'[^\s\(\)]+', give_brackets, tree)
                trees.append(tree)
            tree = ""
    return trees            

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--bracket_file', type=str, required=True, help="Path to parsed sentences (bracketing).")
    parser.add_argument('--format', type=str, required=True, help="Format the corpus should be in. Options are <ccl>, <diora>")
    parser.add_argument('--shapes', type=bool, default=False, help="Whether we run on shapes/natural language.")
    parser.add_argument('--output', type=str, required=True, help="Output filepath without extension.")
    config = parser.parse_args()
    main(config)
