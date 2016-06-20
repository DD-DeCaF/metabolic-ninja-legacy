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


class PathwayGraph(object):
    """
    A possible bug: If a cofactor is presented in exactly 2 reactions and it's not in DEFAULT_COFACTORS,
    it could be counted as a primary metabolite.
    """
    DEFAULT_COFACTORS = {
        'ATP', 'ADP', 'NAD(+)', 'NADH(2-)', 'NADP(+)', 'NADPH',
        'GTP', 'GDP', 'CoA', 'UMP(2-)', 'H(+)', 'O2', 'CO(2)', 'H2O'
    }

    def __init__(self, pathway, product_id):
        self.pathway = pathway
        self.final_product_id = product_id
        pathway_metabolites = reduce(
            lambda x, y: x | y,
            (reaction.metabolites.keys() for reaction in self.pathway.reactions)
        )
        self.all_metabolites = {
            metabolite.id: metabolite for metabolite in pathway_metabolites
        }
        self.all_reactions = {
            m.name: find_reactions_with_metabolite(self.pathway.reactions, m) for m in self.all_metabolites.values()
        }
        self.reactions = {k: v for k, v in self.all_reactions.items() if k not in self.DEFAULT_COFACTORS}
        self.cofactors = set([key for key, reactions in self.all_reactions.items() if len(reactions) > 2])
        self.primary_nodes = {}
        self.graph = nx.DiGraph()
        self.fill_reactions_graph(self.all_metabolites[self.final_product_id], [r for r in self.pathway.reactions], None)
        self.sorted_reactions = nx.topological_sort(self.graph)
        self.sorted_primary_nodes = [self.primary_nodes[reaction] for reaction in self.sorted_reactions]

    def not_secondary_metabolites(self, reaction, metabolite):
        opposites = opposite_metabolites(reaction, metabolite)
        return [o for o in opposites if o.name not in self.DEFAULT_COFACTORS | self.cofactors]

    def fill_reactions_graph(self, start, reactions, prev_reaction):
        rs = find_reactions_with_metabolite(reactions, start)
        # if metabolite participates in more than in 2 reactions in this pathway, it is a cofactor
        # if metabolite participates in less than in 2 reactions, it is a cofactor or the end product
        if len(rs) != 1:
            return
        reaction = rs[0]
        self.primary_nodes[reaction] = start
        if start.id == self.final_product_id:
            self.graph.add_node(reaction)
        else:
            self.graph.add_edge(reaction, prev_reaction)
        primaries = self.not_secondary_metabolites(reaction, start)  # partly duplicates len(rs) check above,
        # but it is needed to remove cofactors which participate in exactly 2 reactions in pathway by chance
        reactions.remove(reaction)
        for primary in primaries:
            self.fill_reactions_graph(primary, reactions, reaction)
