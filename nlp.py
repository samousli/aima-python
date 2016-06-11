"""A chart parser and some grammars. (Chapter 22)"""

# (Written for the second edition of AIMA; expect some discrepanciecs
# from the third edition until this gets reviewed.)

from collections import defaultdict
import networkx as nx
from math import sqrt

# ______________________________________________________________________________
# Grammars and Lexicons


def Rules(**rules):
    """Create a dictionary mapping symbols to alternative sequences.
    >>> Rules(A = "B C | D E")
    {'A': [['B', 'C'], ['D', 'E']]}
    """
    for (lhs, rhs) in rules.items():
        rules[lhs] = [alt.strip().split() for alt in rhs.split('|')]
    return rules


def Lexicon(**rules):
    """Create a dictionary mapping symbols to alternative words.
    >>> Lexicon(Art = "the | a | an")
    {'Art': ['the', 'a', 'an']}
    """
    for (lhs, rhs) in rules.items():
        rules[lhs] = [word.strip() for word in rhs.split('|')]
    return rules


class Grammar:

    def __init__(self, name, rules, lexicon):
        "A grammar has a set of rules and a lexicon."
        self.name = name
        self.rules = rules
        self.lexicon = lexicon
        self.categories = defaultdict(list)
        for lhs in lexicon:
            for word in lexicon[lhs]:
                self.categories[word].append(lhs)

    def rewrites_for(self, cat):
        "Return a sequence of possible rhs's that cat can be rewritten as."
        return self.rules.get(cat, ())

    def isa(self, word, cat):
        "Return True iff word is of category cat"
        return cat in self.categories[word]

    def __repr__(self):
        return '<Grammar %s>' % self.name

E0 = Grammar('E0',
             Rules(  # Grammar for E_0 [Figure 22.4]
                 S='NP VP | S Conjunction S',
                 NP='Pronoun | Name | Noun | Article Noun | Digit Digit | NP PP | NP RelClause',  # noqa
                 VP='Verb | VP NP | VP Adjective | VP PP | VP Adverb',
                 PP='Preposition NP',
                 RelClause='That VP'),

             Lexicon(  # Lexicon for E_0 [Figure 22.3]
                 Noun="stench | breeze | glitter | nothing | wumpus | pit | pits | gold | east",  # noqa
                 Verb="is | see | smell | shoot | fell | stinks | go | grab | carry | kill | turn | feel",  # noqa
                 Adjective="right | left | east | south | back | smelly",
                 Adverb="here | there | nearby | ahead | right | left | east | south | back",  # noqa
                 Pronoun="me | you | I | it",
                 Name="John | Mary | Boston | Aristotle",
                 Article="the | a | an",
                 Preposition="to | in | on | near",
                 Conjunction="and | or | but",
                 Digit="0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9",
                 That="that"
             ))

E_ = Grammar('E_',  # Trivial Grammar and lexicon for testing
             Rules(
                 S='NP VP',
                 NP='Art N | Pronoun',
                 VP='V NP'),

             Lexicon(
                 Art='the | a',
                 N='man | woman | table | shoelace | saw',
                 Pronoun='I | you | it',
                 V='saw | liked | feel'
             ))

E_NP_ = Grammar('E_NP_',  # another trivial grammar for testing
                Rules(NP='Adj NP | N'),
                Lexicon(Adj='happy | handsome | hairy',
                        N='man'))


def generate_random(grammar=E_, s='S'):
    """Replace each token in s by a random entry in grammar (recursively).
    This is useful for testing a grammar, e.g. generate_random(E_)"""
    import random

    def rewrite(tokens, into):
        for token in tokens:
            if token in grammar.rules:
                rewrite(random.choice(grammar.rules[token]), into)
            elif token in grammar.lexicon:
                into.append(random.choice(grammar.lexicon[token]))
            else:
                into.append(token)
        return into

    return ' '.join(rewrite(s.split(), []))

# ______________________________________________________________________________
# Chart Parsing


class Chart:

    """Class for parsing sentences using a chart data structure. [Figure 22.7]
    >>> chart = Chart(E0);
    >>> len(chart.parses('the stench is in 2 2'))
    1
    """

    def __init__(self, grammar, trace=False):
        """A datastructure for parsing a string; and methods to do the parse.
        self.chart[i] holds the edges that end just before the i'th word.
        Edges are 5-element lists of [start, end, lhs, [found], [expects]]."""
        self.grammar = grammar
        self.trace = trace

    def parses(self, words, S='S'):
        """Return a list of parses; words can be a list or string."""
        if isinstance(words, str):
            words = words.split()
        self.parse(words, S)
        # Return all the parses that span the whole input
        # 'span the whole input' => begin at 0, end at len(words)
        return [[i, j, S, found, []]
                for (i, j, lhs, found, expects) in self.chart[len(words)]
                # assert j == len(words)
                if i == 0 and lhs == S and expects == []]

    def parse(self, words, S='S'):
        """Parse a list of words; according to the grammar.
        Leave results in the chart."""
        self.chart = [[] for i in range(len(words)+1)]
        self.add_edge([0, 0, 'S_', [], [S]])
        for i in range(len(words)):
            self.scanner(i, words[i])
        return self.chart

    def add_edge(self, edge):
        "Add edge to chart, and see if it extends or predicts another edge."
        start, end, lhs, found, expects = edge
        if edge not in self.chart[end]:
            self.chart[end].append(edge)
            if self.trace:
                print('Chart: added %s' % (edge,))
            if not expects:
                self.extender(edge)
            else:
                self.predictor(edge)

    def scanner(self, j, word):
        "For each edge expecting a word of this category here, extend the edge."  # noqa
        for (i, j, A, alpha, Bb) in self.chart[j]:
            if Bb and self.grammar.isa(word, Bb[0]):
                self.add_edge([i, j+1, A, alpha + [(Bb[0], word)], Bb[1:]])

    def predictor(self, edge):
        "Add to chart any rules for B that could help extend this edge."
        (i, j, A, alpha, Bb) = edge
        B = Bb[0]
        if B in self.grammar.rules:
            for rhs in self.grammar.rewrites_for(B):
                self.add_edge([j, j, B, [], rhs])

    def extender(self, edge):
        "See what edges can be extended by this edge."
        (j, k, B, _, _) = edge
        for (i, j, A, alpha, B1b) in self.chart[j]:
            if B1b and B == B1b[0]:
                self.add_edge([i, k, A, alpha + [edge], B1b[1:]])


# ______________________________________________________________________________
# CYK Parsing

def CYK_parse(words, grammar):
    "[Figure 23.5]"
    # We use 0-based indexing instead of the book's 1-based.
    N = len(words)
    P = defaultdict(float)
    # Insert lexical rules for each word.
    for (i, word) in enumerate(words):
        for (X, p) in grammar.categories[word]: # XXX grammar.categories needs changing, above
            P[X, i, 1] = p
    # Combine first and second parts of right-hand sides of rules,
    # from short to long.
    for length in range(2, N+1):
        for start in range(N-length+1):
            for len1 in range(1, length): # N.B. the book incorrectly has N instead of length
                len2 = length - len1
                for (X, Y, Z, p) in grammar.cnf_rules(): # XXX grammar needs this method
                    P[X, start, length] = max(P[X, start, length],
                                              P[Y, start, len1] * P[Z, start+len1, len2] * p)
    return P
# Borrowed from: http://hipolabs.com/en/blog/network-analysis-fundamentals/
network = {
    "fatih": ["erdem", "mehmetbarancay", "tayyiperdogdu", "cemal",
              "taylan", "yigit", "serkan", "tuna", "cihanokyay"],
    "cemal": ["taylan", "yigit", "serkan", "sinan"],
    "erdem": ["fatih", "yigit"],
    "taylan": ["yigit", "serkan", "tuna", "cemal"],
    "yigit": ["yigit", "serkan", "tuna", "can"],
    "serkan": ["yigit", "serkan", "tuna", "erdem"],
    "tuna": ["yigit", "taylan", "can"],
    "can": ["yigit", "serkan", "fatih", "sinan"],
    "sinan": ["yigit", "serkan", "fatih", "cemal"],
    "suatavni": ["tayyiperdogdu", "abdullahcicek", "mehmetbarancay"],
    "tayyiperdogdu": ["abdullahcicek", "suatavni", "feyzullahgulen"],
    "abdullahcicek": ["feyzullahgulen"],
    "feyzullahgulen": ["suatavni", "tayyiperdogdu", "suatavni"],
    "mehmetbarancay": ["suatavni", "feyzullahgulen"],
    "cihanokyay": ["fatihkadirakin", "sametatdag", "gokmengorgen"],
    "fatihkadirakin": ["cihanokyay", "berkerpeksag", "johnresig"],
    "sametatdag": ["cihanokyay", "fatihkadirakin", "berkerpeksag"],
    "berkerpeksag": ["cihanokyay", "gokmengorgen"],
    "gokmengorgen": ["cihanokyay", "sametatdag", "berkerpeksag"],
    "eminbugrasakal": ["eminbugrasakal"],
    "johnresig": ["douglescrockford", "addyosmani", "marijnhaverbeke"],
    "addyosmani": ["douglescrockford", "johnresig", "marijnhaverbeke"],
    "trevorburnham": ["douglescrockford", "johnresig", "marijnhaverbeke"],
    "marijnhaverbeke": ["douglescrockford", "addyosmani", "trevorburnham"],
    "douglescrockford": ["martinfowler", "trevorburnham"],
    "martinfowler": ["douglescrockford", "johnresig"],
}


class Page:
    """"""
    def __init__(self, name="", auth=1, hub=1):
        self.name = name
        self.authority = auth
        self.hub = hub

    # def __eq__(self, other):
    #     if isinstance(other, self.__class__):
    #         return self.__dict__ == other.__dict__
    #     else:
    #         return False

    # def __ne__(self, other):
    #     return not self.__eq__(other)

    def __hash__(self):
        return hash(self.name)


class Pages:
    """"""
    def __init__(self, data):
        self.graph = nx.DiGraph()
        # First thing to do is to add the nodes to the graph
        self.graph.add_nodes_from(Page(p) for p in data.keys())

        for pages in data.values():
            for page in pages:
                p = Page(page)
                if p not in self.graph:
                    self.graph.add_node(p)

        # Then we determine the edges on the nodes
        for page, out_links in data.items():
            for out_page in out_links:
                self.graph.add_edge(Page(p), Page(out_page))

    def __iter__(self):
        return self.graph

    def relevant(self, query):
        rel = []
        for page in self.graph:
            # We are modeling queries for page names only
            if page.name == query:
                rel.append(page)
        return rel

    def expand(self, pages):
        expansion = set(pages)
        for p in pages:

            expansion.update(self.graph.predecessors_iter(p))
            expansion.update(self.graph.successors_iter(p))
        return list(expansion)

    def inlinks(self, page):
        return self.graph.predecessors_iter(page)

    def outlinks(self, page):
        return self.graph.successors_iter(page)


def normalize(pages):
    # Calculate sum of square roots for hubs and authorities
    hub_score = sum(sqrt(p.hub) for p in pages)
    auth_score = sum(sqrt(p.authority) for p in pages)

    for p in pages:
        p.hub /= hub_score
        p.authority /= auth_score


def HITS(query, dataset, num_iters=10000):
    pages = dataset.expand(dataset.relevant(query))
    # This is unnecessary, but following the pseudocode closely.
    for p in pages:
        p.hub = 1
        p.authority = 1

    # Since the book doesn't cover any convergence criteria,
    # we repeat the process num_iters times.
    for __ in range(num_iters):
        for p in pages:
            p.authority = sum(inlink.hub for inlink in dataset.inlinks(p))
            p.hub = sum(outlink.authority for outlink in dataset.outlinks(p))

        normalize(pages)
    return pages


r = HITS("fatih", Pages(network))
pr = '\n'.join("{}:\t{}, {}".format(p.name, p.hub, p.authority) for p in r)
print(pr)
