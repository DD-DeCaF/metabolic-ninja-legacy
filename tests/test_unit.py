from collections import namedtuple
from cobra.core import Reaction, Metabolite, Model
from metabolic_ninja.pathway_graph import PathwayGraph


Pathway = namedtuple('Pathway', ['reactions'])


def test_pathway_graph():
    model = Model()
    for m in ['A', 'B', 'C', 'D', 'K', 'L', 'M', 'N']:
        model.add_metabolites([Metabolite(id=m, name=m)])
    reaction1 = Reaction('1')
    reaction2 = Reaction('2')
    reaction3 = Reaction('3')
    model.add_reactions([reaction1, reaction2, reaction3])
    reaction1.build_reaction_from_string('A + B <=> C')
    reaction2.build_reaction_from_string('K + L <=> A + D')
    reaction3.build_reaction_from_string('M + N <=> B')
    pathway_dag = Pathway([reaction1, reaction2, reaction3])
    graph_dag = PathwayGraph(pathway_dag, 'C')
    names = lambda a: [i.name for i in a]
    assert (names(graph_dag.sorted_primary_nodes) == ['A', 'B', 'C']) or \
           (names(graph_dag.sorted_primary_nodes) == ['B', 'A', 'C'])
    pathway_line = Pathway([reaction1, reaction2])
    graph_line = PathwayGraph(pathway_line, 'C')
    assert names(graph_line.sorted_primary_nodes) == ['A', 'C']
