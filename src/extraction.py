from src.utils.typevars import *

from xml.etree.cElementTree import Element, ElementTree

from itertools import groupby, chain


def identify_nodes(nodes: Set[Element]) -> Dict[str, str]:
    coindexed = list(filter(lambda elem: 'index' in elem.attrib.keys(), nodes))
    all_mutual_indices = {i: [node for node in group] for i, group in
                          groupby(sorted(coindexed, key=lambda elem: elem.attrib['index']),
                                  key=lambda elem: elem.attrib['index'])}
    identifying_index = {i: fst(list(map(lambda elem: elem.attrib['id'],
                                         filter(lambda elem: 'cat' in elem.attrib.keys() or 'word' in
                                                             elem.attrib.keys(),
                                                elements))))
                         for i, elements in all_mutual_indices.items()}
    return {n.attrib['id']: identifying_index[n.attrib['index']] if 'index' in n.attrib.keys() else n.attrib['id']
            for n in nodes}


def convert_to_dag(tree: ElementTree) -> DAG:
    nodes = set(tree.iter('node'))
    identifying_indices = identify_nodes(nodes)
    edges = [Edge(source.attrib['id'], target.attrib['id'], target.attrib['rel'])
             for source in nodes for target in source.findall('node')]
    edges = filter(lambda edge: edge.dep != '--', edges)
    edges = set(map(lambda edge: Edge(identifying_indices[edge.source], identifying_indices[edge.target], edge.dep),
                    edges))
    occurring_indices = set.union(set([edge.source for edge in edges]), set([edge.target for edge in edges]))
    occuring_nodes = filter(lambda node: node.attrib['id'] in occurring_indices or 'word' in node.attrib.keys(), nodes)
    attribs = {node.attrib['id']: node.attrib for node in occuring_nodes}
    return DAG(set(attribs.keys()), edges, attribs)


def _cats_of_type(dag: DAG, cat: Dep) -> List[Node]:
    return list(filter(lambda node: 'cat' in dag.attribs[node] and dag.attribs[node]['cat'] == cat, dag.nodes))


def order_siblings(dag: DAG, nodes: Nodes) -> List[Node]:
    return sorted(nodes, key=lambda node: tuple(map(int, (dag.attribs[node]['begin'],
                                                          dag.attribs[node]['end'],
                                                          dag.attribs[node]['id']))))

def majority_vote(x: Any) -> Any:
    return 'MAJORITY VOTED'


def remove_abstract_arguments(dag: DAG, candidates: Iterable[Dep] = ('su', 'obj', 'obj1', 'obj2', 'sup')):
    def has_sentential_parent(node: Node) -> bool:
        return any(list(map(lambda n: dag.attribs[n.source]['cat'] in ('sv1', 'smain', 'ssub'),
                            dag.incoming(node))))

    def is_candidate_dep(edge: Edge) -> bool:
        return edge.dep in candidates

    def is_coindexed(node: Node) -> bool:
        return len(dag.incoming(node)) > 1

    def is_inf_or_ppart(node: Node) -> bool:
        return dag.attribs[node]['cat'] in ('ppart', 'inf')

    for_removal = set(filter(lambda e: is_candidate_dep(e) and is_coindexed(e.target) and is_inf_or_ppart(e.source)
                                       and has_sentential_parent(e.target), dag.edges))

    return dag.remove_edges(lambda e: e not in for_removal)


def collapse_mwu(dag: DAG) -> DAG:
    mwus = _cats_of_type(dag, 'mwu')
    successors = list(map(lambda mwu: order_siblings(dag, dag.successors(mwu)), mwus))
    collapsed_texts = list(map(lambda suc: ' '.join([dag.attribs[s]['word'] for s in suc]), successors))
    for mwu, succ, text in zip(mwus, successors, collapsed_texts):
        dag.attribs[mwu]['word'] = text
        del dag.attribs[mwu]['cat']
        dag.attribs[mwu]['pt'] = majority_vote(succ)
    to_delete = set(list(chain.from_iterable(map(dag.outgoing, mwus))))
    if to_delete:
        from src.viz import ToGraphViz
        ToGraphViz()(dag)
        import pdb
        pdb.set_trace()
        dag = dag.remove_edges(lambda e: e not in to_delete)
        ToGraphViz()(dag)
        pdb.set_trace()
    return dag.remove_edges(lambda e: e not in to_delete)






