import functools

import jax
import jax.numpy as jnp
import numpy as np
import pandas as pd
from jax import config
from jax.ops import index
from jax.ops import index_update

from skillmodels.constraints import add_bounds
from skillmodels.constraints import constraints
from skillmodels.kalman_filters import calculate_sigma_scaling_factor_and_weights
from skillmodels.kalman_filters import kalman_predict
from skillmodels.kalman_filters import kalman_update
from skillmodels.params_index import params_index
from skillmodels.parse_params import create_parsing_info
from skillmodels.parse_params import parse_params
from skillmodels.process_data import process_data_for_estimation
from skillmodels.process_model import process_model

config.update("jax_enable_x64", True)


def get_maximization_inputs(model_dict, data):
    """Create inputs for estimagic's maximize function.

    Args:
        model_dict (dict): The model specification. See: :ref:`model_specs`
        dataset (DataFrame): dataset in long format.

    Returns:
        loglike (function): A jax jitted function that takes an estimagic-style
            params dataframe as only input and returns the a dict with the entries:
            - "value": The scalar log likelihood
            - "contributions": An array with the log likelihood per observation
            - "all_contributions": A pandas DataFrame with the log likelihood of each
                Kalman update.
        debug_loglike (function): Same as loglike but not jitted. This
            can be used to find out quickly if the likelihood function is defined at
            the start params (because the jitted version takes long on the first run)
            or to step through it with a debugger.
        gradient (function): The gradient of the scalar log likelihood
            function with respect to the parameters.
        loglike_and_gradient (function): Combination of loglike and
            loglike_gradient that is faster than calling the two functions separately.
        constraints (list): List of estimagic constraints that are implied by the
            model specification.
        params_template (pd.DataFrame): Parameter DataFrame with correct index and
            bounds but with empty value column.

    """
    model = process_model(model_dict)
    p_index = params_index(model["update_info"], model["labels"], model["dimensions"])

    parsing_info = create_parsing_info(
        p_index, model["update_info"], model["labels"], model["dimensions"]
    )
    measurements, controls, anchoring_variables = process_data_for_estimation(
        data, model["labels"], model["update_info"], model["anchoring"]
    )

    sigma_scaling_factor, sigma_weights = calculate_sigma_scaling_factor_and_weights(
        model["dimensions"]["n_states"], model["options"]["sigma_points_scale"]
    )

    _loglike = functools.partial(
        _log_likelihood_jax,
        parsing_info=parsing_info,
        update_info=model["update_info"],
        measurements=measurements,
        controls=controls,
        transition_functions=model["transition_functions"],
        sigma_scaling_factor=sigma_scaling_factor,
        sigma_weights=sigma_weights,
        anchoring_variables=anchoring_variables,
        dimensions=model["dimensions"],
        labels=model["labels"],
        options=model["options"],
    )

    _jitted_loglike = jax.jit(_loglike)
    _gradient = jax.grad(_jitted_loglike, has_aux=True)

    def debug_loglike(params):
        params_vec = jnp.array(params["value"].to_numpy())
        jax_output = _loglike(params_vec)[1]
        numpy_output = _to_numpy(jax_output)
        numpy_output["value"] = float(numpy_output["value"])
        return numpy_output

    def loglike(params):
        params_vec = jnp.array(params["value"].to_numpy())
        jax_output = _jitted_loglike(params_vec)[1]
        numpy_output = _to_numpy(jax_output)
        numpy_output["value"] = float(numpy_output["value"])
        return numpy_output

    def gradient(params):
        params_vec = jnp.array(params["value"].to_numpy())
        jax_output = _gradient(params_vec)[0]
        return _to_numpy(jax_output)

    def loglike_and_gradient(params):
        params_vec = jnp.array(params["value"].to_numpy())
        jax_grad, jax_crit = _gradient(params_vec)
        numpy_grad = _to_numpy(jax_grad)
        numpy_crit = _to_numpy(jax_crit)
        numpy_crit["value"] = float(numpy_crit["value"])
        return numpy_crit, numpy_grad

    constr = constraints(
        dimensions=model["dimensions"],
        labels=model["labels"],
        anchoring_info=model["anchoring"],
        update_info=model["update_info"],
        normalizations=model["normalizations"],
    )

    params_template = pd.DataFrame(columns=["value"], index=p_index)
    params_template = add_bounds(params_template, model["options"]["bounds_distance"])

    out = {
        "loglike": loglike,
        "debug_loglike": debug_loglike,
        "gradient": gradient,
        "loglike_and_gradient": loglike_and_gradient,
        "constraints": constr,
        "params_template": params_template,
    }

    return out


def _log_likelihood_jax(
    params,
    parsing_info,
    update_info,
    measurements,
    controls,
    transition_functions,
    sigma_scaling_factor,
    sigma_weights,
    anchoring_variables,
    dimensions,
    labels,
    options,
):
    """Log likelihood of a skill formation model.

    This function is jax-differentiable and jax-jittable as long as all but the first
    argument are marked as static.

    In contrast to most likelihood functions this returns both an aggregated likelihood
    value and the likelihood contribution of each individual.

    Args:
        params (jax.numpy.array): 1d array with model parameters.
        parsing_info (dict): Contains information how to parse parameter vector.
        update_info (pandas.DataFrame): Contains information about number of updates in
            each period and purpose of each update.
        measurements (jax.numpy.array): Array of shape (n_updates, n_obs) with data on
            observed measurements. NaN if the measurement was not observed.
        controls (jax.numpy.array): Array of shape (n_periods, n_obs, n_controls)
            with observed control variables for the measurement equations.
        transition_functions (tuple): tuple of tuples where the first element is the
            name of the transition function and the second the actual transition
            function. Order is important and corresponds to the latent
            factors in alphabetical order.
        sigma_scaling_factor (float): A scaling factor that controls the spread of the
            sigma points. Bigger means that sigma points are further apart. Depends on
            the sigma_point algorithm chosen.
        sigma_weights (jax.numpy.array): 1d array of length n_sigma with non-negative
            sigma weights.
        anchoring_variables (jax.numpy.array): Array of shape (n_periods, n_obs, n_fac)
            with anchoring outcomes. Can be 0 for unanchored factors or if no centering
            is desired.
        dimensions (dict): Dimensional information like n_states, n_periods, n_controls,
            n_mixtures. See :ref:`dimensions`.
        labels (dict): Dict of lists with labels for the model quantities like
            factors, periods, controls, stagemap and stages. See :ref:`labels`

    Returns:
        jnp.array: 1d array of length 1, the aggregated log likelihood.
        jnp.array: Array of shape (n_obs, n_updates) log likelihood contributions per
            individual and update.

    """
    n_obs = measurements.shape[1]
    states, upper_chols, log_mixture_weights, pardict = parse_params(
        params, parsing_info, dimensions, labels, n_obs
    )
    n_updates = len(update_info)
    loglikes = jnp.zeros((n_updates, n_obs))

    k = 0
    for t in labels["periods"]:
        nmeas = len(update_info.loc[t])
        for _j in range(nmeas):
            purpose = update_info.iloc[k]["purpose"]
            new_states, new_upper_chols, new_weights, loglikes_k = kalman_update(
                states,
                upper_chols,
                pardict["loadings"][k],
                pardict["controls"][k],
                pardict["meas_sds"][k],
                measurements[k],
                controls[t],
                log_mixture_weights,
            )
            loglikes = index_update(loglikes, index[k], loglikes_k)
            log_mixture_weights = new_weights
            if purpose == "measurement":
                states, upper_chols = new_states, new_upper_chols

            k += 1

        if t != labels["periods"][-1]:
            states, upper_chols = kalman_predict(
                states,
                upper_chols,
                sigma_scaling_factor,
                sigma_weights,
                transition_functions,
                pardict["transition"][t],
                pardict["shock_sds"][t],
                pardict["anchoring_scaling_factors"][t : t + 2],
                anchoring_variables[t : t + 2],
            )

        clipped = soft_clipping(
            arr=loglikes,
            lower=options["clipping_lower_bound"],
            upper=options["clipping_upper_bound"],
            lower_hardness=options["clipping_lower_hardness"],
            upper_hardness=options["clipping_upper_hardness"],
        )

        value = clipped.sum()

        additional_data = {
            # used for scalar optimization, thus has to be clipped
            "value": value,
            # can be used for sum optimizers, thus has to be clipped
            "contributions": clipped.sum(axis=0),
        }
        if options["return_all_contributions"]:
            additional_data["all_contributions"] = loglikes

    return value, additional_data


def soft_clipping(arr, lower=None, upper=None, lower_hardness=1, upper_hardness=1):
    """Clip values in an array elementwise using a soft maximum to avoid kinks.

    Clipping from below is taking a maximum between two values. Clipping
    from above is taking a minimum, but it can be rewritten as taking a maximum after
    switching the signs.

    To smooth out the kinks introduced by normal clipping, we first rewrite all clipping
    operations to taking maxima. Then we replace the normal maximum by the soft maximum.

    For background on the soft maximum check out this
    `article by John Cook: <https://www.johndcook.com/soft_maximum.pdf>`_

    Note that contrary to the name, the soft maximum can be calculated using
    ``scipy.special.logsumexp``. ``scipy.special.softmax`` is the gradient of
    ``scipy.special.logsumexp``.


    Args:
        arr (jax.numpy.array): Array that is clipped elementwise.
        lower (float): The value at which the array is clipped from below.
        upper (float): The value at which the array is clipped from above.
        lower_hardness (float): Scaling factor that is applied inside the soft maximum.
            High values imply a closer approximation of the real maximum.
        upper_hardness (float): Scaling factor that is applied inside the soft maximum.
            High values imply a closer approximation of the real maximum.

    """
    shape = arr.shape
    flat = arr.flatten()
    dim = len(flat)
    if lower is not None:
        helper = jnp.column_stack([flat, jnp.full(dim, lower)])
        flat = (
            jax.scipy.special.logsumexp(lower_hardness * helper, axis=1)
            / lower_hardness
        )
    if upper is not None:
        helper = jnp.column_stack([-flat, jnp.full(dim, -upper)])
        flat = (
            -jax.scipy.special.logsumexp(upper_hardness * helper, axis=1)
            / upper_hardness
        )
    return flat.reshape(shape)


def _to_numpy(obj):
    if isinstance(obj, dict):
        res = {}
        for key, value in obj.items():
            if np.isscalar(value):
                res[key] = value
            else:
                res[key] = np.array(value)

    elif np.isscalar(obj):
        res = obj
    else:
        res = np.array(obj)

    return res
