import sys
import numpy as np
import cPickle as pkl
import shutil

from config import *
from model import GAReaderMatrix
from utils import Helpers, DataPreprocessor, MiniBatchLoader

def main(load_path, params, mode='test'):

    regularizer = params['regularizer']
    rlambda = params['lambda']
    nhidden = params['nhidden']
    dropout = params['dropout']
    word2vec = params['word2vec']
    dataset = params['dataset']
    nlayers = params['nlayers']
    train_emb = params['train_emb']
    subsample = params['subsample']
    base_model = params['model']
    char_dim = params['char_dim']
    use_feat = params['use_feat']
    gating_fn = params['gating_fn']

    # load settings
    shutil.copyfile('%s/config.py'%load_path,'config.py')

    dp = DataPreprocessor.DataPreprocessor()
    data = dp.preprocess(dataset)
    inv_vocab = data.inv_dictionary

    print("building minibatch loaders ...")
    if mode=='test':
        batch_loader_test = MiniBatchLoader.MiniBatchLoader(data.test, BATCH_SIZE, data.dictionary)
    else:
        batch_loader_test = MiniBatchLoader.MiniBatchLoader(data.validation, BATCH_SIZE, data.dictionary)

    print("building network ...")
    W_init, embed_dim = Helpers.load_word2vec_embeddings(data.dictionary[0], word2vec)
    m = eval(base_model).Model(nlayers, data.vocab_size, data.num_chars, W_init, 
            regularizer, rlambda, nhidden, embed_dim, dropout, train_emb, subsample, 
            char_dim, use_feat, data.dictionary[4])
    m.load_model('%s/best_model.p'%load_path)

    print("testing ...")
    pr = np.zeros((len(batch_loader_test.questions),
        batch_loader_test.max_num_cand)).astype('float32')
    fids, attns = [], []
    total_loss, total_acc, n = 0., 0., 0
    for dw, dt, qw, qt, a, m_dw, m_qw, tt, tm, c, m_c, cl, fnames, match_feat, use_char, use_char_q in batch_loader_test:
        outs = m.validate(dw, dt, qw, qt, c, a, m_dw, m_qw, tt, tm, m_c, cl, match_feat, use_char, use_char_q)
        loss, acc, probs = outs[:3]
        attns += [[fnames[0],probs[0,:]] + [o[0,:,:] for o in outs[3:]]] # store one attention

        bsize = dw.shape[0]
        total_loss += bsize*loss
        total_acc += bsize*acc

        pr[n:n+bsize,:] = probs
        fids += fnames
        n += bsize

    logger = open(load_path+'/log','a',0)
    message = '%s Loss %.4e acc=%.4f' % (mode.upper(), total_loss/n, total_acc/n)
    print message
    logger.write(message+'\n')
    logger.close()

    np.save('%s/%s.probs' % (load_path,mode),np.asarray(pr))
    pkl.dump(attns, open('%s/%s.attns' % (load_path,mode),'w'))
    f = open('%s/%s.ids' % (load_path,mode),'w')
    for item in fids: f.write(item+'\n')
    f.close()
