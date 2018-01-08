from collections import namedtuple
from cobra.core import Reaction, Model
from metabolic_ninja.app import map_metabolites_ids_to_bigg


Pathway = namedtuple('Pathway', ['reactions'])


def test_map_metabolites_ids_to_bigg():
    model = Model()
    reaction1 = Reaction('1')
    reaction2 = Reaction('2')
    model.add_reactions([reaction1, reaction2])
    reaction1.build_reaction_from_string('MNXM1671 + MNXM1747 <=> MNXM1251')
    reaction2.build_reaction_from_string('impossible <=> MNXM1747')
    pathway = Pathway([reaction1, reaction2])
    map_metabolites_ids_to_bigg(pathway)
    assert set([m.id for m in pathway.reactions[0].metabolites]) == \
           {'itaccoa_c', 'itacon_c', 'citmcoa__L_c'}
    assert set([m.id for m in pathway.reactions[1].metabolites]) == \
           {'impossible', 'itacon_c'}