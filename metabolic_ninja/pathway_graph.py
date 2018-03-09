#Copyright 2018 Novo Nordisk Foundation Center for Biosustainability, DTU.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import reduce
import networkx as nx


def find_reactions_with_metabolite(reactions, metabolite):
    result = []
    for reaction in reactions:
        if metabolite in reaction.metabolites:
            result.append(reaction)
    return result


def opposite_metabolites(reaction, metabolite):
    sign = reaction.metabolites[metabolite] > 0
    result = []
    for met, coef in reaction.metabolites.items():
        if (coef > 0) != sign:
            result.append(met)
    return result


# TODO: If a cofactor is presented in exactly 2 reactions
# and it's not in DEFAULT_COFACTORS, it could be counted
# as a primary metabolite.
class PathwayGraph(object):
    DEFAULT_COFACTORS = {
        'ATP', 'ADP', 'NAD(+)', 'NADH(2-)', 'NADP(+)', 'NADPH',
        'GTP', 'GDP', 'CoA', 'UMP(2-)', 'H(+)', 'O2', 'CO(2)',
        'H2O', 'H2O2', 'CO2', 'NADH', 'NADP', 'NAD', 'H', 'UMP',
        'AMP'
    }

    def __init__(self, pathway, product):
        self.pathway = pathway
        self.final_product = product
        pathway_metabolites = reduce(
            lambda x, y: x | y,
            (reaction.metabolites.keys() for reaction in self.pathway.reactions)
        )
        self.all_metabolites = {
            metabolite.name: metabolite for metabolite in pathway_metabolites
        }
        self.all_reactions = {
            m.name: find_reactions_with_metabolite(self.pathway.reactions, m) for m in self.all_metabolites.values()
        }
        self.reactions = {k: v for k, v in self.all_reactions.items() if k not in self.DEFAULT_COFACTORS}
        self.cofactors = set([key for key, reactions in self.all_reactions.items() if len(reactions) > 2])
        self.primary_nodes = {}
        self.graph = nx.DiGraph()
        self._fill_reactions_graph(self.all_metabolites[self.final_product], [r for r in self.pathway.reactions], None)
        self.sorted_reactions = list(nx.topological_sort(self.graph))
        self.sorted_primary_nodes = [self.primary_nodes[reaction] for reaction in self.sorted_reactions]

    def _not_secondary_metabolites(self, reaction, metabolite):
        opposites = opposite_metabolites(reaction, metabolite)
        return [o for o in opposites if o.name not in self.DEFAULT_COFACTORS | self.cofactors]

    def _fill_reactions_graph(self, start, reactions, prev_reaction):
        rs = find_reactions_with_metabolite(reactions, start)
        # if metabolite participates in more than in 2 reactions in this pathway, it is a cofactor
        # if metabolite participates in less than in 2 reactions, it is a cofactor or the end product
        if len(rs) != 1:
            return
        reaction = rs[0]
        self.primary_nodes[reaction] = start
        if start.name == self.final_product:
            self.graph.add_node(reaction)
        else:
            self.graph.add_edge(reaction, prev_reaction)
        primaries = self._not_secondary_metabolites(reaction, start)  # partly duplicates len(rs) check above,
        # but it is needed to remove cofactors which participate in exactly 2 reactions in pathway by chance
        reactions.remove(reaction)
        for primary in primaries:
            self._fill_reactions_graph(primary, reactions, reaction)
