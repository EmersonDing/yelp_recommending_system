#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import pickle

import numpy as np
import pandas as pd
import similarity
from model import Simple_sim, Topk
from scipy import sparse


def preprocess_data(fname):
    names = ['user_id', 'item_id', 'rating', 'timestamp']
    df = pd.read_csv(fname, sep='\t', names=names)

    user_id = {uid: i for i, uid in enumerate(set(df["user_id"]))}
    item_id = {iid: i for i, iid in enumerate(set(df["item_id"]))}

    n_users = df.user_id.unique().shape[0]
    n_items = df.item_id.unique().shape[0]

    ratings = []
    count= []
    row_ind = []
    col_ind = []
    for _, row in df.iterrows():
        row_ind.append(user_id[row[0]])
        col_ind.append(item_id[row[1]])
        ratings.append(row[2])
        count.append(1)

    # One user might rate one item multiple times, we calculate the avrage for that.
    count_mat = sparse.csr_matrix((count, (row_ind, col_ind)), shape=(n_users, n_items), dtype=float)
    ui_mat = sparse.csr_matrix((ratings, (row_ind, col_ind)), shape=(n_users, n_items), dtype=float)

    # Do the average
    count_mat.data = 1/count_mat.data
    ui_mat = ui_mat.multiply(count_mat)

    return ui_mat


def train_test_split(ui_mat, split=0.1):
    train_mat = ui_mat.copy()
    test_mat = ui_mat.copy()
    for i in range(ui_mat.shape[0]):
        cols = ui_mat.getrow(i).indices
        cols = np.random.permutation(cols)
        cut = int(split*len(cols))
        test_ind = cols[:cut]
        train_ind = cols[cut:]

        test_mat[i, train_ind] = 0
        train_mat[i, test_ind] = 0

    train_mat.eliminate_zeros()
    test_mat.eliminate_zeros()

    # Training and testing should be disjoint
    assert((train_mat.multiply(test_mat)).sum() == 0)
    return train_mat, test_mat


def get_mse(pred, actual):
    pred = np.asarray(pred).flatten()
    actual = np.asarray(actual[actual.nonzero()]).flatten()
    assert(len(pred)==len(actual))
    return np.sum((pred-actual)**2)/len(pred)


def doIt(modelCls, user_based=True, item_based=True, **model_args):
    '''Compare different models.
    @modelCls class: The class of the target model.
    @param doItemBased: boolean. WHether to do item based method by transposing the matrix.
    @param model_args: args for initializing modelCls.
    '''
    print
    print('='*20)
    print('Model: {}'.format(modelCls.__name__))
    print('Args: {}'.format(model_args))
    if user_based:
        user_model = modelCls(**model_args)
        user_model.train(train_mat, test_mat)
        user_prediction = user_model.predict(train_mat, test_mat)
        print('User-based CF MSE: {}'.format(get_mse(user_prediction, test_mat)))

    if item_based:
        train_matT, test_matT = train_mat.T.tocsr(), test_mat.T.tocsr()
        item_model = modelCls(**model_args)
        item_model.train(train_matT, test_matT)
        item_prediction = item_model.predict(train_matT, test_matT)
        print('Item-based CF MSE: {}'.format(get_mse(item_prediction, test_matT)))


if __name__ == '__main__':
    np.random.seed(0)

    if not os.path.isfile('./data.pkl'):
        ui_mat = preprocess_data('../u.data')
        train_mat, test_mat = train_test_split(ui_mat, 0.1)
        with open('data.pkl', 'w') as f:
            pickle.dump({'train':train_mat, 'test': test_mat}, f)
    else:
        with open('data.pkl', 'r') as f:
            data = pickle.load(f)
            train_mat, test_mat = data['train'], data['test']

    # Note: simple_sim is just TopK with k=\infty
    doIt(Simple_sim, sim_fn=similarity.cosine_sim)
    doIt(Topk, k=50, sim_fn=similarity.cosine_sim)
