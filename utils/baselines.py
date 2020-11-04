"""
Classes for creating baseline messages or grammars.
"""

import numpy as np
from nltk import CFG, Nonterminal
from nltk.parse.generate import generate
from pathlib import Path
import random
import argparse

class AbstractBaseline:
    """Abstract class for baseline classes"""
    def __init__(self, directory, name):
        self.directory = Path(directory)
        self.name = name

    def load_grammar(self):
        """Return grammar if already exists in directory, otherwise None"""
        return None

    def generate_messages(self):
        raise NotImplementedError

    def save_messages(self, ratio=0.8, max_messages=5000, max_messages_split=2000, shuffle=True):
        """Generate baseline messages and save to file in two splits"""

        # Create file with all messages (name_full.txt)
        file_name = self.name + "_full.txt"
        message_file = self.directory / file_name
        
        ## Check if message file already exist, otherwise save messages to file
        if not message_file.exists():
            with open(message_file, 'w') as f:
                newline = ""
                for i, m in enumerate(self.generate_messages()):
                    if m: # ignore empty messages
                        f.write(newline+" ".join(m))
                        newline="\n"
                    if max_messages:
                        if i>max_messages:
                            break

        # Create train and test splits
        with open(message_file, 'r') as f:
            messages = f.read().splitlines()
            number_to_keep = int(ratio * len(messages))
            if max_messages_split:
                number_to_keep = min(number_to_keep, max_messages_split)

        if shuffle:
            random.shuffle(messages)

        messages_induct = messages[:number_to_keep]
        messages_eval = messages[number_to_keep:]

        file_name_induct = self.name + "_induct.txt"
        induct_file = self.directory / file_name_induct

        file_name_eval = self.name + "_eval.txt"
        eval_file = self.directory / file_name_eval

        if not induct_file.exists():
            with open(induct_file, 'w') as f:
                newline = ""
                for m in messages_induct:
                    f.write(newline+m)
                    newline="\n"
        if not eval_file.exists():
            with open(eval_file, 'w') as f:
                newline = ""
                for m in messages_eval:
                    f.write(newline+m)
                    newline="\n"

class StructuredBaseline(AbstractBaseline):
    """Class for creating and loading structured baselines for vocab size V and message length L"""
    
    def __init__(self, V, L, directory, name="struct_baseline", grammar_dir=None):
        """Initialise the structured baseline"""
        #self.name = name
        name = name if name else "struct_baseline"
        super().__init__(directory, name)
        self.grammar_dir = Path(grammar_dir) if grammar_dir else None
        self.grammar = self.create_grammar(V, L)
        self.save_grammar(V, L)

    def save_grammar(self, V, L):
        
        if self.grammar_dir:
            if not self.grammar_dir.is_dir():
                self.grammar_dir.mkdir()
            grammar_fp = self.grammar_dir / f"V{V}L{L}.cfg"
            
            if not grammar_fp.exists():
                #grammar_fp.write_text(str(self.grammar))
                grammar_fp.write_text(('\n').join([str(prod) for prod in self.grammar.productions()]))

    def create_grammar(self, V, L):
        """Create a simple hierarchical grammar if it does not already exist.

        Parameters
        ----------
        V : int
            vocabulary size, should be > 3.
        L : int >3
            message length, should be > 2.

        Returns
        -------
        grammar : nltk.CFG
        """
        
        assert V>3, "V is too small, the minimum vocabulary size is 4."
        assert L>2, "L is too small, the minimum message length is 3."
        
        grammar = self.load_grammar()

        # Create a structured grammar if it does not exist already
        if not grammar:
            # List of letters a-z for the grammar
            alphabet = [chr(i) for i in range(ord('a'),ord('z')+1)]

            # Sublists with words for each pos tag
            words = list(range(0,V))
            num_pos = max(V-2, 4) if V<L else L
            if V==6 and L==5:
                num_pos = L-1
            chunks = [list(i) for i in np.array_split(words,num_pos)]

            ### Create the grammar string

            grammar_string = "TOP ->"

            # Create nominal group string
            nominal_group = " NP"

            sep = ""
            grammar_string += sep + nominal_group + f" AP" + " | "
            grammar_string += f"AP" + nominal_group
            sep = " |"
            if L>3:
                grammar_string += " |" + nominal_group + f" VP" + nominal_group

            # Lexical rule for NP
            newline = "\n"

            grammar_string += newline+nominal_group+" -> "+alphabet[0]+" "+alphabet[1]

            # Lexical rule for AP and VP, alternating pos tags (c d c d c d etc.)
            grammar_string += newline+"AP -> " + " ".join([alphabet[i%(num_pos-2)+2] for i in range(2,L)])

            if L>3:
                grammar_string += newline+"VP -> " + " ".join([alphabet[i%(num_pos-2)+2] for i in range(2,L-2)])

            # Create a lexical rule for each pos tag
            for i in range(0,num_pos):
                rule = f"{alphabet[i]} -> "
                sep = ""
                for word in chunks[i]:
                    rule += sep + "'" + str(word) + "'"
                    sep = " | "
                grammar_string += newline + rule

            grammar = CFG.fromstring(grammar_string)
            grammar._start = Nonterminal('TOP')

        return grammar

    def generate_messages(self):
        """
        Generates messages for a synthetic structured language 
        according to a simple grammar, not randomly.

        Yields
        ------
        message : list
            A list with each element a word (str) in the message.
        """
        for message in generate(self.grammar):
            yield message

class ShuffledBaseline(AbstractBaseline):
    """Class for creating and loading shuffled baselines"""
    
    def __init__(self, emergent, directory, name="shuf_baseline"):
        """Initialise the structured baseline

        Parameters
        ----------
        emergent : str
            Path to emergent language messages
        """
        name = name if name else "shuf_baseline"
        super().__init__(directory, name)
        self.emergent = Path(emergent)
        self.grammar = None

    def generate_messages(self):
        """
        Generates messages by shuffling all emergent language messages.

        Yields
        ------
        message : list
            A list with each element a word (str) in the message.
        """
        with open(self.emergent, 'r') as f:
            messages = f.read().splitlines()
           
        for message in messages:
            shuffled_message = message.split()
            random.shuffle(shuffled_message)
            yield shuffled_message

class RandomBaseline(AbstractBaseline):
    """Class for creating and loading random baselines"""
    
    def __init__(self, emergent, directory, name="rand_baseline"):
        """Initialise the random baseline

        Parameters
        ----------
        emergent : str
            Path to emergent language messages
        """
        name = name if name else "rand_baseline"
        super().__init__(directory, name)
        self.emergent = Path(emergent)
        self.grammar = None

    def sample_message(self, L,vocabulary):
        """
        Sample message from the generation space of size V^L.

        Parameters
        ----------
        L: int
            Message length of the language.
        vocabulary : list
            Vocabulary to sample symbols from.

        Returns
        ------
        message: list
            A list with each element a word (str) in the message.
        """
        message = []
        for i in range(0,L):
            message.append(random.choice(vocabulary))

        return message

    def get_vocabulary_and_lengths(self):
        """Extracts vocabulary and message lengths from the emergent messages"""
        with open(self.emergent, 'r') as f:
            messages = f.read().splitlines()

        vocab = set()
        message_lengths = []
        for message in messages:
            m = message.split()
            vocab.update(m)
            message_lengths.append(len(m))
        
        return list(vocab), message_lengths

    def generate_messages(self):
        """
        Generates messages by sampling from vocab with same message lengths 
        as emergent language messages.

        Yields
        ------
        message : list
            A list with each element a word (str) in the message.
        """
        
        vocab, message_lengths = self.get_vocabulary_and_lengths()

        for l in message_lengths:
            yield self.sample_message(l, vocab)
            
if __name__=='__main__':
    """
    Example usage
    -------------
    print("Structured Baseline")
    v=13
    l=10
    baseline = StructuredBaseline(v, l, "data/baselines")
    print(baseline.grammar)
    print(next(baseline.generate_messages()))
    baseline.save_messages()

    print("\nShuffled Baseline")
    baseline = ShuffledBaseline("data/demo_language.txt","data/baselines")
    print(next(baseline.generate_messages()))
    baseline.save_messages()
    
    print("\nRandom Baseline")
    baseline = RandomBaseline("data/demo_language.txt","data/baselines")
    print(next(baseline.generate_messages()))
    baseline.save_messages()
    """
    parser = argparse.ArgumentParser(description='Arguments for generating baselines.')
    parser.add_argument('--baseline',
                        default='shuf',
                        const='shuf',
                        choices=('shuf','rand','struct'),
                        nargs='?',
                        help='Baseline to generate; either shuf, rand, or struct (default: %(default)s)'
    )
    parser.add_argument('--directory',
                        default='data',
                        type=str,
                        help='Directory where to save the baseline messages.'
    )
    parser.add_argument('--grammar_dir',
                        default='results/grammars/structured_grammar',
                        type=str,
                        help='Directory where to load and save the structured baseline grammar.'
    )
    parser.add_argument('--name',
                        default=None,
                        help='Name of the baseline.'
    )
    parser.add_argument('-V',
                        default=None,
                        type=int,
                        help='Vocabulary size, minimum size 4. Required for struct baseline.'
    )
    parser.add_argument('-L',
                        default=None,
                        type=int,
                        help='Message length, minimum size 3. Required for struct baseline.'
    )
    parser.add_argument('--emergent',
                        type=str,
                        default=False,
                        help='File path of emergent language messages; required for shuffled and random baselines.'
    )

    args = parser.parse_args()
    
    if args.baseline == 'struct':
        assert args.V, 'A vocabulary size (flag -V) is required for the structured baseline.'
        assert args.L, 'A message length (flag -L) is required for the structured baseline.'
        baseline = StructuredBaseline(args.V, args.L, args.directory, name=args.name, grammar_dir=args.grammar_dir)
    elif args.baseline == 'shuf':
        assert args.emergent, "File path to messages (flag --emergent) required for this baseline."
        baseline = ShuffledBaseline(args.emergent, args.directory, name=args.name)
    elif args.baseline == 'rand':
        assert args.emergent, "File path to messages (flag --emergent) required for this baseline."
        baseline = RandomBaseline(args.emergent, args.directory, name=args.name)

    baseline.save_messages()
