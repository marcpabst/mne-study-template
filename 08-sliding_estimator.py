"""
=================
Sliding estimator
=================

A sliding estimator fits a logistic regression model for every time point.
In this example, we contrast the condition 'famous' against 'scrambled'
using this approach. The end result is an averaging effect across sensors.
The contrast across different sensors are combined into a single plot.

"""  # noqa: E501

###############################################################################
# Let us first import the libraries

import os.path as op
import logging

import numpy as np
from scipy.io import savemat

import mne
from mne.decoding import SlidingEstimator, cross_val_multiscore

from mne_bids import BIDSPath

from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.linear_model import LogisticRegression

import config
from config import gen_log_message, on_error, failsafe_run

logger = logging.getLogger('mne-study-template')


def run_time_decoding(subject, condition1, condition2, session=None):
    msg = f'Contrasting conditions: {condition1} – {condition2}'
    logger.info(gen_log_message(message=msg, step=8, subject=subject,
                                session=session))

    fname_in = BIDSPath(subject=subject,
                        session=session,
                        task=config.get_task(),
                        acquisition=config.acq,
                        run=None,
                        recording=config.rec,
                        space=config.space,
                        suffix='epo',
                        extension='.fif',
                        datatype=config.get_datatype(),
                        root=config.deriv_root,
                        check=False)

    epochs = mne.read_epochs(fname_in)

    # We define the epochs and the labels
    epochs = mne.concatenate_epochs([epochs[condition1],
                                     epochs[condition2]])
    epochs.apply_baseline()

    # Get the data and labels
    X = epochs.get_data()
    n_cond1 = len(epochs[condition1])
    n_cond2 = len(epochs[condition2])
    y = np.r_[np.ones(n_cond1), np.zeros(n_cond2)]

    se = SlidingEstimator(
        make_pipeline(StandardScaler(),
                      LogisticRegression(solver='liblinear',
                                         random_state=config.random_state)),
        scoring=config.decoding_metric, n_jobs=config.N_JOBS)
    scores = cross_val_multiscore(se, X=X, y=y, cv=config.decoding_n_splits)

    # let's save the scores now
    a_vs_b = f'{condition1}-{condition2}'.replace(op.sep, '')
    processing = f'{a_vs_b}+{config.decoding_metric}'
    processing = processing.replace('_', '-').replace('-', '')
    fname_td = fname_in.copy().update(suffix='decoding',
                                      processing=processing,
                                      extension='.mat')
    savemat(fname_td, {'scores': scores, 'times': epochs.times})


@failsafe_run(on_error=on_error)
def main():
    """Run sliding estimator."""
    msg = 'Running Step 8: Sliding estimator'
    logger.info(gen_log_message(step=8, message=msg))

    if not config.contrasts:
        msg = 'No contrasts specified; not performing decoding.'
        logger.info(gen_log_message(step=8, message=msg))
        return

    if not config.decode:
        msg = 'No decoding requested by user.'
        logger.info(gen_log_message(step=8, message=msg))
        return

    # Here we go parallel inside the :class:`mne.decoding.SlidingEstimator`
    # so we don't dispatch manually to multiple jobs.
    for subject in config.get_subjects():
        for session in config.get_sessions():
            for contrast in config.contrasts:
                cond_1, cond_2 = contrast
                run_time_decoding(subject=subject, condition1=cond_1,
                                  condition2=cond_2, session=session)

    msg = 'Completed Step 8: Sliding estimator'
    logger.info(gen_log_message(step=8, message=msg))


if __name__ == '__main__':
    main()
