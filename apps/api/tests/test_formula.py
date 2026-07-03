"""Tests for the safe formula evaluator.

Covers: correctness, missing vars, division by zero, injection security.
"""

import pytest

from api.formula import (
    DivisionByZeroError,
    FormulaError,
    MissingVariableError,
    eval_formula,
)


class TestFormulaEvaluation:
    def test_simple_division(self):
        result = eval_formula("Rb / Sr", {"Rb": 200.0, "Sr": 59.0})
        assert abs(result - 3.389830508474576) < 0.001

    def test_simple_addition(self):
        result = eval_formula("Rb + Sr", {"Rb": 100.0, "Sr": 50.0})
        assert result == 150.0

    def test_simple_subtraction(self):
        result = eval_formula("Rb - Sr", {"Rb": 100.0, "Sr": 50.0})
        assert result == 50.0

    def test_simple_multiplication(self):
        result = eval_formula("Rb * Sr", {"Rb": 10.0, "Sr": 20.0})
        assert result == 200.0

    def test_complex_expression_with_parentheses(self):
        result = eval_formula("(Rb + Sr) / Ba", {"Rb": 100.0, "Sr": 50.0, "Ba": 30.0})
        assert abs(result - 5.0) < 0.001

    def test_unary_minus(self):
        result = eval_formula("-Rb", {"Rb": 42.0})
        assert result == -42.0

    def test_numeric_literals(self):
        result = eval_formula("42 + Rb", {"Rb": 8.0})
        assert result == 50.0

    def test_float_literals(self):
        result = eval_formula("3.14 * Rb", {"Rb": 2.0})
        assert abs(result - 6.28) < 0.001

    # --- Reference numbers from paleoclimate XRF ---

    def test_reference_5621_6_rb_sr(self):
        """sample 5621_6 → Rb/Sr ≈ 3.39"""
        result = eval_formula("Rb / Sr", {"Rb": 200.0, "Sr": 59.0})
        assert abs(result - 3.39) < 0.01

    def test_reference_5621_6_al_si(self):
        """sample 5621_6 → Al/Si ≈ 0.64"""
        result = eval_formula("Al / Si", {"Al": 9.0, "Si": 14.0})
        assert abs(result - 0.64) < 0.01

    def test_reference_6821_6_rb_sr(self):
        """sample 6821-6 → Rb/Sr ≈ 0.86"""
        result = eval_formula("Rb / Sr", {"Rb": 113.0, "Sr": 131.0})
        assert abs(result - 0.86) < 0.01

    def test_reference_6821_6_al_si(self):
        """sample 6821-6 → Al/Si ≈ 0.25"""
        result = eval_formula("Al / Si", {"Al": 4.3, "Si": 17.2})
        assert abs(result - 0.25) < 0.01

    # --- Error handling ---

    def test_missing_variable(self):
        with pytest.raises(MissingVariableError):
            eval_formula("Rb / Sr", {"Rb": 100.0})  # Sr missing

    def test_division_by_zero(self):
        with pytest.raises(DivisionByZeroError):
            eval_formula("Rb / Sr", {"Rb": 100.0, "Sr": 0.0})


class TestFormulaInjectionSecurity:
    """Security boundary: formulas must never execute arbitrary code."""

    def test_rejects_import(self):
        with pytest.raises(FormulaError):
            eval_formula("__import__('os').system('ls')", {})

    def test_rejects_attr_access(self):
        with pytest.raises(FormulaError):
            eval_formula("Rb.__class__", {"Rb": 1.0})

    def test_rejects_lambda(self):
        with pytest.raises(FormulaError):
            eval_formula("(lambda x: x)(42)", {})

    def test_rejects_function_call_syntax(self):
        with pytest.raises(FormulaError):
            eval_formula("exec('pass')", {})

    def test_rejects_list_access(self):
        with pytest.raises(FormulaError):
            eval_formula("x[0]", {"x": [1, 2, 3]})

    def test_rejects_dict_access(self):
        with pytest.raises(FormulaError):
            eval_formula("x['key']", {"x": {"key": 1}})

    def test_rejects_underscore_vars(self):
        """Underscore-prefixed vars might be Python internals."""
        with pytest.raises(MissingVariableError):
            # '_Rb' is a valid variable name in formulas, but won't be in symbol table
            eval_formula("_Rb / Sr", {"Sr": 1.0})

    def test_rejects_string_literals(self):
        with pytest.raises(FormulaError):
            eval_formula("'string'", {})

    def test_empty_formula(self):
        with pytest.raises(FormulaError):
            eval_formula("", {})

    def test_gibberish_formula(self):
        with pytest.raises(FormulaError):
            eval_formula("!@#$%^", {})

    def test_rejects_truthy_comparison(self):
        with pytest.raises(FormulaError):
            eval_formula("Rb > Sr", {"Rb": 1.0, "Sr": 2.0})

    def test_rejects_assignment(self):
        with pytest.raises(FormulaError):
            eval_formula("Rb = 42", {"Rb": 1.0})
