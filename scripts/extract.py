from LassyExtraction.utils.lassy import Lassy
from LassyExtraction.utils.graph import DAG
from LassyExtraction.transformations import prepare_many, get_lex_nodes
from LassyExtraction.aethel import Sample, Premise
from LassyExtraction.extraction import prove, ExtractionError
import os


name_to_subset = {name: subset for name, subset in
                  map(lambda x: x.split('\t'), open('./data/name_to_subset.tsv').read().splitlines())}


def get_premises(dag: DAG[str], attrs: tuple[str, ...]) -> list[tuple]:
    lex_nodes = get_lex_nodes(dag)
    return [tuple(dag.get(node, attr) for attr in attrs) for node in lex_nodes]


def make_sample(dag: DAG[str]) -> Sample:
    term = prove(dag)
    term = term.canonicalize_var_names()
    premises = get_premises(dag, ('word', 'pos', 'pt', 'lemma', 'proof'))
    term = term.translate_lex({premise[-1].constant: i for i, premise in enumerate(premises)})
    return Sample(
        premises=[Premise(word=word, pos=pos, pt=pt, lemma=lemma, type=type(lex))
                  for word, pos, pt, lemma, lex in premises],
        proof=term,
        name=(name := dag.meta['name']),
        subset=name_to_subset[name.split('(')[0]])


def store_aethel(version: str,
                 transform_path: str = './data/transformed.pickle',
                 save_intermediate: bool = False,
                 output_path: str = f'./data/aethel.pickle') -> None:
    import pickle
    if save_intermediate or not os.path.exists(transform_path):
        lassy = Lassy()
        print('Transforming LASSY trees...')
        transformed = prepare_many(lassy)
        with open(transform_path, 'wb') as f:
            print('Saving transformed trees...')
            pickle.dump(transformed, f)
            print('Done.')
    else:
        with open(transform_path, 'rb') as f:
            print('Loading transformed trees...')
            transformed = pickle.load(f)
            print('Loaded.')

    print('Proving transformed trees...')
    train, dev, test = [], [], []
    for tree in transformed:
        try:
            sample = make_sample(tree)
        except ExtractionError:
            continue
        (train if sample.subset == 'train' else dev if sample.subset == 'dev' else test).append(sample)
    print(f'Proved {(l:=sum(map(len, (train, dev, test))))} samples. (coverage: {l / len(transformed)})')
    print('Saving samples...')
    with open(output_path, 'wb') as f:
        pickle.dump((version, [[sample.save() for sample in subset] for subset in (train, dev, test)]), f)
    print('Done.')


if __name__ == '__main__':
    store_aethel('0.9.dev0')