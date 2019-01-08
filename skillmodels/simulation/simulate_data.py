"""Functions to simulate a dataset generated by a latent factor model.

Notes:
    - I use abbreviations to describe the sizes of arrays. An overview is here:
        https://skillmodels.readthedocs.io/en/latest/names_and_concepts.html
    - what is called factors here is the same as states in the assignments.
    - You can use additional functions if you want. Their name should start
        with an underscore to make clear that those functions should not be
        used in any other module.
    - Please write tests for all functions except simulate_dataset.
        I know that functions involving randomness are hard to test. The
        best way is to replace (patch) the methods that actually generate
        random numbers with a so called mock function while testing. It can
        be done with this library:
        https://docs.python.org/3/library/unittest.mock.html
        I do similar stuff in many places of skillmodels but it is quite difficult,
        so you can also ask me once you get there and we can do it together.
    - The tests should be in a module in
        `skillmodels/tests/simulation/simulate_dataset_test.py.
    - Use pytest for the tests (as you learned in the lecture) even though
        the other tests in skillmodels use an older library
    - I added some import statements but you will probably need more
    - Please delete all notes in the docstrings when you are done.
    - It is very likely that I made some mistakes in the docstrings or forgot an
        argument somewhere. Just send me an email in that case or come to my office.

"""
import skillmodels.model_functions.transition_functions as tf
from numpy.random import multivariate_normal


def simulate_datasets():
    """Simulate datasets generated by a latent factor model.

    This function calls the remaining functions in this module.

    Implement this function at the very end and only after I accepted your pull
    request for the remaining functions. You can then either figure out a suitable
    list of arguments yourself or ask me again.

    Returns:
        observed_data (pd.DataFrame): Dataset with measurements and control variables
            in long format
        latent_data (pd.DataFrame): Dataset with lantent factors in long format
    """
    pass


def generate_start_factors_and_control_variables(
        means, covs, weights, nobs, factor_names, control_names):
    """Draw initial states and control variables from a (mixture of) normals.

    Args:
        means (np.ndarray): size (nemf, nfac + ncontrols)
        covs (np.ndarray): size (nemf, nfac + ncontrols, nfac + ncontrols)
        weights (np.ndarray): size (nemf). The weight of each mixture element.
        nobs (int): number of observations

    Returns:
        start_factors (pd.DataFrame): shape (nobs, nfac),
            columns are factor_names
        controls (pd.DataFrame): shape (nobs, ncontrols),
            columns are control names

    Notes:
        In the long run I would like to generalize this to drawing from a mixture of
        elliptical distributions: https://en.wikipedia.org/wiki/Elliptical_distribution
        This contains the multivariate normal as a special case.
        It would require an interface change because the elliptical distribution has more
        parameters than just mean and covariance. It would be great if you make a proposal
        for this general case.

    """
    pass


def next_period_factors(
        factors, transition_names, transition_argument_dicts, shock_variances):
    """Apply transition function to factors and add shocks.

    Args:
        factors (pd.DataFrame): shape (nobs, nfac)
        transition_names (list): list of strings with the names of the transition
            function of each factor.
        transition_argument_dicts (list): list of dictionaries of length nfac with
            the arguments for the transition function of each factor. A detailed description
            of the arguments of transition functions can be found in the module docstring
            of skillmodels.model_functions.transition_functions.
        shock_variances (np.ndarray): numpy array of length nfac.

    Returns:
        next_factors (pd.DataFrame):

    Notes:
        - You can look at the module `transform_sigma_points` to see how you can use
        getattr() to call the transition functions based on their name

        - Writing this function is quite complex because it reuses a lot of code for
             the transition functions. Take the time to read the documentation of those
             functions if you feel it is necessary

        - The shocks for the different factors are assumed to be independent. You can draw
            them from a multivariate normal with diagonal covariance matrix or from
            nfac univariate normals.

        - You have to convert the factors to a numpy array (DataFrame.values) and then convert
            the result back in the end. For speed reasons all the transition functions
            expect numpy arrays and not pandas DataFrames.


    """
    pass


def measurements_from_factors(factors, controls, loadings, deltas, variances, measurement_names):
    """Generate the variables that would be observed in practice.

    This generates the data for only one period. Let nmeas be the number of measurements in that period.

    Args:
        factors (pd.DataFrame): DataFrame of shape (nobs, nfac)
        controls (pd.DataFrame): DataFrame of shape (nobs, ncontrols)
        loadings (np.ndarray): numpy array of size (nmeas, nfac)
        deltas (np.ndarray): numpy array of size (nmeas, ncontrols)
        variances (np.ndarray): numpy array of size (nmeas) with the variances of the
            measurements. Measurement error is assumed to be independent across measurements
        measurement_names (list): list of length nmeas with the names of the measurements

    Returns:
        measurements (pd.DataFrame): DataFrame of shape (nobs, nmeas) with measurement
            names as columns.

    Notes:
        - A measurement y is a linear function of latent factors and control variables, i.e.
            y = factors times loadings + controls times deltas + epsilon
            This is a slide extension of the measurement model you know from the assignments.
        - Try to express as much as possible in matrix products. This will lead to concise and
            fast code.
    """
    pass