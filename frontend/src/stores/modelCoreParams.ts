import type { ModelTypeInfo } from '../api/modelingApi';

type ModelFamily =
    | 'linear'
    | 'tree'
    | 'ensemble'
    | 'boosting'
    | 'svm'
    | 'neighbors'
    | 'neural';

const FAMILY_PARAM_OVERRIDES: Record<ModelFamily, string[]> = {
    linear: ['alpha', 'C', 'l1_ratio', 'fit_intercept'],
    tree: ['n_estimators', 'max_depth', 'min_samples_split', 'min_samples_leaf'],
    ensemble: ['n_estimators', 'max_depth', 'min_samples_split', 'min_samples_leaf'],
    boosting: ['n_estimators', 'learning_rate', 'max_depth', 'subsample'],
    svm: ['kernel', 'C', 'gamma', 'epsilon'],
    neighbors: ['n_neighbors', 'weights', 'p'],
    neural: ['hidden_layer_sizes', 'activation', 'alpha', 'learning_rate_init', 'max_iter'],
};

function inferFamilies(model: ModelTypeInfo): ModelFamily[] {
    const families = new Set<ModelFamily>();
    const category = model.category ?? '';
    const name = model.name.toLowerCase();

    if (category === 'linear' || name.includes('linear') || name.includes('ridge') || name.includes('lasso')) {
        families.add('linear');
    }
    if (category === 'tree' || name.includes('tree')) {
        families.add('tree');
    }
    if (
        category === 'ensemble' ||
        name.includes('forest') ||
        name.includes('boost') ||
        name.includes('ensemble')
    ) {
        families.add('ensemble');
    }
    if (name.includes('boost')) {
        families.add('boosting');
    }
    if (category === 'svm' || name.includes('svr')) {
        families.add('svm');
    }
    if (category === 'neighbors' || name.includes('neighbor')) {
        families.add('neighbors');
    }
    if (category === 'neural_network' || name.includes('mlp') || name.includes('neural')) {
        families.add('neural');
    }
    return Array.from(families);
}

export function getAlwaysVisibleModelParams(model: ModelTypeInfo): Set<string> {
    const names = new Set<string>();
    model.parameters
        .filter((param) => param.ui_group === 'core')
        .forEach((param) => names.add(param.name));

    inferFamilies(model).forEach((family) => {
        (FAMILY_PARAM_OVERRIDES[family] ?? []).forEach((name) => names.add(name));
    });

    return names;
}
