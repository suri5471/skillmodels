"""Contains functions that are needed for the WA estimator."""

import numpy as np


def loadings_from_covs(data, normalization, storage_df):
    """Factor loadings of measurements of one factor in the first.

    Calculate the factor loadings of all measurements of one factor in the
    first period as average of ratios of covariances. For this to be possible,
    at least three  measurement variables have to be available in the dataset.
    The result is stored in storage_df

    Args:
        data (DataFrame): pandas DataFrame with the measurement data for one
            factor in one period.
        normalization (list): The first value is the name of a normalized
            measurement, the second is the value it is normalized to.
        storage_df (DataFrame): DataFrame in which the results are stored

    """
    t = 0
    measurements = list(data.columns)
    nmeas = len(measurements)
    assert nmeas >= 3, (
        'For covariance based factor loading estimation 3 or more '
        'measurements are needed.')

    cov = data.cov()
    load_norm, load_norm_val = normalization

    for m in measurements:
        if m != load_norm:
            estimates = []
            for m_prime in measurements:
                if m_prime not in [m, load_norm]:
                    nominator = cov.loc[m, m_prime]
                    denominator = load_norm_val * cov.loc[load_norm, m_prime]
                    estimates.append(nominator / denominator)
            storage_df.loc[(t, m), 'loadings'] = np.mean(estimates)


def intercepts_from_means(data, normalization, storage_df, mean_list):
    """Calculate intercepts and factor means for 1 factor in the first period.

    If the normalization list is not empty, it is assumed that the factor
    mean is not normalized and has to be estimated. In this case, the factor
    mean is calculated first and appended to the mean_list. Later the
    non-normalized intercepts are calculated and stored in storage_df.

    Args:
        data (DataFrame): pandas DataFrame with the measurement data for one
            factor in one period.
        normalization (list): The first value is the name of a normalized
            measurement, the second is the value it is normalized to.
        storage_df (DataFrame): DataFrame in which the results are stored
        mean_list (list): a list to which the estimated mean is appended

    """
    t = 0
    measurements = list(data.columns)
    if len(normalization) == 0:
        for meas in measurements:
            storage_df.loc[(t, meas), 'intercepts'] = data[meas].mean()
    else:
        intercept_norm, intercept_norm_val = normalization
        loading = storage_df.loc[(t, intercept_norm), 'loadings']
        estimated_factor_mean = \
            (data[intercept_norm].mean() - intercept_norm_val) / loading
        mean_list.append(estimated_factor_mean)

        for m, meas in enumerate(measurements):
            if meas != intercept_norm:
                loading = storage_df.loc[(t, meas), 'loadings']
                storage_df.loc[(t, meas), 'intercepts'] = \
                    data[meas].mean() - loading * estimated_factor_mean