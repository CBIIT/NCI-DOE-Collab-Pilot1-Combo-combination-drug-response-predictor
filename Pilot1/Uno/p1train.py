#! /usr/bin/env python

import argparse
import os
import numpy as np
import pandas as pd
import random
from skwrapper import regress, classify, train, split_data


MODELS = ['LightGBM', 'RandomForest', 'XGBoost']
CV = 3
THREADS = 4
OUT_DIR = 'p1save'
BINS = 0
CUTOFFS = None
FEATURE_SUBSAMPLE = 0
SEED = 2018


def get_parser(description='Run machine learning training algorithms implemented in scikit-learn'):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("-b", "--bins", type=int, default=BINS,
                        help="number of evenly distributed bins to make when classification mode is turned on")
    parser.add_argument("-c", "--classify",  action="store_true",
                        help="convert the regression problem into classification based on category cutoffs")
    parser.add_argument("-d", "--data",
                        help="data file to train on")
    parser.add_argument("-g", "--groupcols", nargs='+',
                        help="names of columns to be used in cross validation partitioning")
    parser.add_argument("-m", "--models", nargs='+', default=MODELS,
                        help="list of regression models: XGBoost, XGB.1K, XGB.10K, RandomForest, RF.1K, RF.10K, AdaBoost, Linear, ElasticNet, Lasso, Ridge; or list of classification models: XGBoost, XGB.1K, XGB.10K, RandomForest, RF.1K, RF.10K, AdaBoost, Logistic, Gaussian, Bayes, KNN, SVM")
    parser.add_argument("-o", "--out_dir", default=OUT_DIR,
                        help="output directory")
    parser.add_argument("-p", "--prefix",
                        help="output prefix")
    parser.add_argument("-t", "--threads", type=int, default=THREADS,
                        help="number of threads per machine learning training job; -1 for using all threads")
    parser.add_argument("-y", "--ycol", default='0',
                        help="0-based index or name of the column to be predicted")
    parser.add_argument("--cutoffs", nargs='+', type=float, default=CUTOFFS,
                        help="list of cutoffs delineating prediction target categories")
    parser.add_argument("--cv", type=int, default=CV,
                        help="cross validation folds")
    parser.add_argument("--feature_subsample", type=int, default=FEATURE_SUBSAMPLE,
                        help="number of features to randomly sample from each category, 0 means using all features")
    parser.add_argument("-C", "--ignore_categoricals", action='store_true',
                        help="ignore categorical feature columns")
    parser.add_argument("--seed", type=int, default=SEED,
                        help="specify random seed")
    return parser


def set_seed(seed):
    os.environ['PYTHONHASHSEED'] = '0'
    np.random.seed(seed)
    random.seed(seed)


def main():
    parser = get_parser()
    args = parser.parse_args()
    set_seed(args.seed)

    prefix = args.prefix or os.path.basename(args.data)
    prefix = os.path.join(args.out_dir, prefix)

    df = pd.read_table(args.data, engine='c')
    cat_cols = df.select_dtypes(['object']).columns
    if args.ignore_categoricals:
        df[cat_cols] = 0
    else:
        df[cat_cols] = df[cat_cols].apply(lambda x: x.astype('category').cat.codes)

    x, y, splits, features = split_data(df, ycol=args.ycol, classify=args.classify,
                                        cv=args.cv, bins=args.bins, cutoffs=args.cutoffs,
                                        groupcols=args.groupcols, verbose=True)

    if args.classify and len(np.unique(y)) < 2:
        print('Not enough classes\n')
        return

    best_score, best_model = 0, None
    for model in args.models:
        if args.classify:
            score = classify(model, x, y, splits, features, threads=args.threads, prefix=prefix, seed=args.seed)
        else:
            score = regress(model, x, y, splits, features, threads=args.threads, prefix=prefix, seed=args.seed)
        if score >= best_score:
            best_score = score
            best_model = model

    print(best_model)
    print('Training the best model ({}={:.3g}) on the entire dataset...'.format(best_model, best_score))
    name = 'best.classifier' if args.classify else 'best.regressor'
    fname = train(best_model, x, y, features, classify=args.classify,
                  threads=args.threads, prefix=prefix, name=name, save=True)
    print('Model saved in {}\n'.format(fname))


if __name__ == '__main__':
    main()