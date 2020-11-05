# Languages emerging in a simple referential game
This dataset contains the emergent languages used for the experiments in ['The Grammar of Emergent Languages'](https://arxiv.org/pdf/2010.02069).

## Data
Each file contains messages from an emergent language defined by its message length L, vocabulary size V, and seed s.
For instance, language `V6L10s1` has vocabulary size 6, message length 10, and seed 1.
The following prefixes are used to denote:
- `_orig`: the induction set;
- `_full`: the full data-set before dividing over the splits;
- `_eval`: the evaluation set;
- `_shuf`: the shuffled baseline;
- `_rand`: the random baseline.

The number of messages per language and other details on the languages and their baselines can be found in the paper.

## Acknowledgements
These emergent languages come from a referential game designed and implemented by Diana Luna Rodrı́guez.
