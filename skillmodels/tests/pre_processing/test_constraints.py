import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from skillmodels.pre_processing.constraints import _ar1_contraints
from skillmodels.pre_processing.constraints import _constant_factors_constraints
from skillmodels.pre_processing.constraints import _invariant_meas_system_constraints
from skillmodels.pre_processing.constraints import _normalization_constraints
from skillmodels.pre_processing.constraints import _not_measured_constraints
from skillmodels.pre_processing.constraints import _p_constraints
from skillmodels.pre_processing.constraints import _stage_constraints
from skillmodels.pre_processing.constraints import _trans_coeff_constraints
from skillmodels.pre_processing.constraints import _w_constraints
from skillmodels.pre_processing.constraints import _x_constraints
from skillmodels.pre_processing.constraints import add_bounds


def test_add_bounds():
    ind_tups = [("q", i) for i in range(5)] + [("r", 4), ("bla", "blubb"), ("r", "foo")]
    df = pd.DataFrame(
        index=pd.MultiIndex.from_tuples(ind_tups),
        data=np.arange(16).reshape(8, 2),
        columns=["lower", "upper"],
    )
    expected = df.copy(deep=True)
    expected["lower"] = [0.1] * 5 + [0.1, 12, 0.1]

    calculated = add_bounds(df, 0.1)
    assert_frame_equal(calculated, expected)


def test_invariant_meas_system_constraints():
    ind_tups = [(0, "m1"), (0, "m2"), (1, "m1"), (1, "m3"), (2, "m1"), (2, "m3")]
    uinfo = pd.DataFrame(index=pd.MultiIndex.from_tuples(ind_tups))
    uinfo["is_repeated"] = [False, False, True, False, True, True]
    uinfo["first_occurence"] = [np.nan, np.nan, 0, np.nan, 0, 1]
    controls = [["cont"]] * 3
    factors = ["fac1", "fac2"]

    expected = [
        {
            "loc": [("delta", 1, "m1", "constant"), ("delta", 0, "m1", "constant")],
            "type": "equality",
        },
        {
            "loc": [("delta", 1, "m1", "cont"), ("delta", 0, "m1", "cont")],
            "type": "equality",
        },
        {"loc": [("h", 1, "m1", "fac1"), ("h", 0, "m1", "fac1")], "type": "equality"},
        {"loc": [("h", 1, "m1", "fac2"), ("h", 0, "m1", "fac2")], "type": "equality"},
        {"loc": [("r", 1, "m1", ""), ("r", 0, "m1", "")], "type": "equality"},
        {
            "loc": [("delta", 2, "m1", "constant"), ("delta", 0, "m1", "constant")],
            "type": "equality",
        },
        {
            "loc": [("delta", 2, "m1", "cont"), ("delta", 0, "m1", "cont")],
            "type": "equality",
        },
        {"loc": [("h", 2, "m1", "fac1"), ("h", 0, "m1", "fac1")], "type": "equality"},
        {"loc": [("h", 2, "m1", "fac2"), ("h", 0, "m1", "fac2")], "type": "equality"},
        {"loc": [("r", 2, "m1", ""), ("r", 0, "m1", "")], "type": "equality"},
        {
            "loc": [("delta", 2, "m3", "constant"), ("delta", 1, "m3", "constant")],
            "type": "equality",
        },
        {
            "loc": [("delta", 2, "m3", "cont"), ("delta", 1, "m3", "cont")],
            "type": "equality",
        },
        {"loc": [("h", 2, "m3", "fac1"), ("h", 1, "m3", "fac1")], "type": "equality"},
        {"loc": [("h", 2, "m3", "fac2"), ("h", 1, "m3", "fac2")], "type": "equality"},
        {"loc": [("r", 2, "m3", ""), ("r", 1, "m3", "")], "type": "equality"},
    ]

    calculated = _invariant_meas_system_constraints(uinfo, controls, factors)

    assert_list_equal_except_for_order(calculated, expected)


def test_normalization_constraints():
    norm = {
        "fac1": {
            "loadings": [{"m1": 2, "m2": 1.5}, {"m1": 3}],
            "intercepts": [{"m1": 0.5}, {}],
            "variances": [{}, {"m1": 1}],
        },
        "fac2": {
            "loadings": [{"m3": 1}, {}],
            "intercepts": [{}, {}],
            "variances": [{}, {}],
        },
    }

    expected = [
        {"loc": ("h", 0, "m1", "fac1"), "type": "fixed", "value": 2},
        {"loc": ("h", 0, "m2", "fac1"), "type": "fixed", "value": 1.5},
        {"loc": ("h", 1, "m1", "fac1"), "type": "fixed", "value": 3},
        {"loc": ("delta", 0, "m1", "constant"), "type": "fixed", "value": 0.5},
        {"loc": ("r", 1, "m1", ""), "type": "fixed", "value": 1},
        {"loc": ("h", 0, "m3", "fac2"), "type": "fixed", "value": 1},
    ]

    calculated = _normalization_constraints(norm)
    assert_list_equal_except_for_order(calculated, expected)


def test_not_measured_constraints():
    ind_tups = [(0, "m1"), (0, "m2"), (0, "m3"), (1, "m1"), (1, "m3")]
    uinfo = pd.DataFrame(index=pd.MultiIndex.from_tuples(ind_tups))

    measurements = {"fac1": [["m1", "m2"], ["m1"]], "fac2": [["m2", "m3"], ["m3"]]}

    expected = [
        {"loc": ("h", 0, "m1", "fac2"), "type": "fixed", "value": 0.0},
        {"loc": ("h", 0, "m3", "fac1"), "type": "fixed", "value": 0.0},
        {"loc": ("h", 1, "m1", "fac2"), "type": "fixed", "value": 0.0},
        {"loc": ("h", 1, "m3", "fac1"), "type": "fixed", "value": 0.0},
    ]

    calculated = _not_measured_constraints(uinfo, measurements, [], None)

    assert_list_equal_except_for_order(calculated, expected)


def test_w_constraints_mixture():
    calculated = _w_constraints(nemf=2)
    expected = [{"loc": "w", "type": "probability"}]
    assert_list_equal_except_for_order(calculated, expected)


def test_w_constraints_normal():
    calculated = _w_constraints(nemf=1)
    expected = [{"loc": "w", "type": "fixed", "value": 1.0}]
    assert_list_equal_except_for_order(calculated, expected)


def test_p_constraints():
    nemf = 2
    expected = [
        {"loc": ("p", 0, 0), "type": "covariance", "bounds_distance": 0.0},
        {"loc": ("p", 0, 1), "type": "covariance", "bounds_distance": 0.0},
    ]

    calculated = _p_constraints(nemf, 0.0)
    assert_list_equal_except_for_order(calculated, expected)


def test_stage_constraints():
    factors = ["fac1"]
    stagemap = [0, 0, 0, 0]
    transition_names = ["linear_with_constant"]
    included_factors = [["fac1"]]

    expected = [
        {
            "loc": [
                ("trans", 0, "fac1", "lincoeff-fac1"),
                ("trans", 1, "fac1", "lincoeff-fac1"),
            ],
            "type": "equality",
        },
        {
            "loc": [
                ("trans", 0, "fac1", "lincoeff-constant"),
                ("trans", 1, "fac1", "lincoeff-constant"),
            ],
            "type": "equality",
        },
        {"loc": [("q", 0, "fac1", ""), ("q", 1, "fac1", "")], "type": "equality"},
        {
            "loc": [
                ("trans", 1, "fac1", "lincoeff-fac1"),
                ("trans", 2, "fac1", "lincoeff-fac1"),
            ],
            "type": "equality",
        },
        {
            "loc": [
                ("trans", 1, "fac1", "lincoeff-constant"),
                ("trans", 2, "fac1", "lincoeff-constant"),
            ],
            "type": "equality",
        },
        {"loc": [("q", 1, "fac1", ""), ("q", 2, "fac1", "")], "type": "equality"},
    ]

    calculated = _stage_constraints(
        stagemap, factors, transition_names, included_factors
    )
    assert_list_equal_except_for_order(calculated, expected)


def test_constant_factor_constraints():
    factors = ["fac1", "fac2"]
    periods = [0, 1, 2]
    transition_names = ["bla", "constant"]

    expected = [
        {"loc": ("q", 0, "fac2", ""), "type": "fixed", "value": 0.0},
        {"loc": ("q", 1, "fac2", ""), "type": "fixed", "value": 0.0},
    ]

    calculated = _constant_factors_constraints(factors, transition_names, periods)
    assert_list_equal_except_for_order(calculated, expected)


def test_ar1_constraints():
    factors = ["fac1", "fac2"]
    periods = [0, 1, 2, 3]
    transition_names = ["bla", "ar1"]
    included_factors = [["fac1", "fac2"], ["fac2"]]

    expected = [
        {
            "loc": [("trans", 0, "fac2", "ar1coeff"), ("trans", 1, "fac2", "ar1coeff")],
            "type": "equality",
        },
        {
            "loc": [("trans", 1, "fac2", "ar1coeff"), ("trans", 2, "fac2", "ar1coeff")],
            "type": "equality",
        },
        {"loc": [("q", 0, "fac2", ""), ("q", 1, "fac2", "")], "type": "equality"},
        {"loc": [("q", 1, "fac2", ""), ("q", 2, "fac2", "")], "type": "equality"},
    ]
    calculated = _ar1_contraints(factors, transition_names, included_factors, periods)
    assert_list_equal_except_for_order(calculated, expected)


def test_x_constraints():
    nemf = 3
    factors = ["fac1", "fac2", "fac3"]
    ind_tups = [("x", 0, 0, "fac1"), ("x", 0, 1, "fac1"), ("x", 0, 2, "fac1")]

    expected = [{"loc": ind_tups, "type": "increasing"}]

    calculated = _x_constraints(nemf, factors, True)
    assert_list_equal_except_for_order(calculated, expected)


def test_trans_coeff_constraints():
    factors = ["fac1", "fac2", "fac3"]
    transition_names = ["log_ces", "bla", "blubb"]
    included_factors = [["fac1", "fac2", "fac3"], [], []]
    periods = [0, 1, 2]

    expected = [
        {
            "loc": [
                ("trans", 0, "fac1", "gamma-fac1"),
                ("trans", 0, "fac1", "gamma-fac2"),
                ("trans", 0, "fac1", "gamma-fac3"),
            ],
            "type": "probability",
        },
        {
            "loc": [
                ("trans", 1, "fac1", "gamma-fac1"),
                ("trans", 1, "fac1", "gamma-fac2"),
                ("trans", 1, "fac1", "gamma-fac3"),
            ],
            "type": "probability",
        },
    ]
    calculated = _trans_coeff_constraints(
        factors, transition_names, included_factors, periods
    )

    assert_list_equal_except_for_order(calculated, expected)


# ======================================================================================


def assert_list_equal_except_for_order(list1, list2):
    for item in list1:
        assert item in list2, f"{item} is in list1 but not in list2"
    for item in list2:
        assert item in list1, f"{item} is in list2 but not in list1"