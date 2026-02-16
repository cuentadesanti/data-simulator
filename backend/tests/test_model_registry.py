"""Tests for the enhanced model registry with auto-discovery.

This module tests the model registry auto-discovery, parameter enrichment,
and UI grouping features.
"""

from __future__ import annotations

from app.services.model_registry import (
    ADVANCED_PARAMS,
    CORE_PARAMS,
    INTERNAL_PARAMS,
    ModelParameter,
    ModelRegistry,
    _class_name_to_snake_case,
    _discover_sklearn_regressors,
    _extract_sklearn_params,
    _get_param_ui_group,
    get_model_registry,
)

# =============================================================================
# Auto-Discovery Tests
# =============================================================================


class TestAutoDiscovery:
    """Tests for sklearn regressor auto-discovery."""

    def test_discover_returns_regressors(self):
        """Test that auto-discovery finds sklearn regressors."""
        discovered = _discover_sklearn_regressors()
        
        assert len(discovered) > 10  # Should find many regressors
        names = [d["name"] for d in discovered]
        
        # Common regressors should be present
        assert "linear_regression" in names
        assert "ridge" in names
        assert "random_forest_regressor" in names
        assert "svr" in names

    def test_discover_excludes_meta_estimators(self):
        """Test that meta-estimators are excluded."""
        discovered = _discover_sklearn_regressors()
        names = [d["name"] for d in discovered]
        
        # Meta-estimators should be excluded
        assert "stacking_regressor" not in names
        assert "voting_regressor" not in names
        assert "multi_output_regressor" not in names

    def test_discover_sets_category(self):
        """Test that categories are correctly assigned."""
        discovered = _discover_sklearn_regressors()
        
        # Find specific models and check categories
        linear = next(d for d in discovered if d["name"] == "linear_regression")
        rf = next(d for d in discovered if d["name"] == "random_forest_regressor")
        svr = next(d for d in discovered if d["name"] == "svr")
        
        assert linear["category"] == "linear"
        assert rf["category"] == "ensemble"
        assert svr["category"] == "svm"

    def test_class_name_to_snake_case(self):
        """Test CamelCase to snake_case conversion."""
        assert _class_name_to_snake_case("LinearRegression") == "linear_regression"
        assert _class_name_to_snake_case("RandomForestRegressor") == "random_forest_regressor"
        assert _class_name_to_snake_case("SVR") == "svr"
        assert _class_name_to_snake_case("MLPRegressor") == "mlp_regressor"


# =============================================================================
# Parameter Enrichment Tests
# =============================================================================


class TestParameterEnrichment:
    """Tests for parameter metadata enrichment."""

    def test_param_ui_group_core(self):
        """Test that core parameters are identified."""
        for param in CORE_PARAMS:
            assert _get_param_ui_group(param) == "core"

    def test_param_ui_group_internal(self):
        """Test that internal parameters are identified."""
        for param in INTERNAL_PARAMS:
            assert _get_param_ui_group(param) == "internal"

    def test_param_ui_group_advanced(self):
        """Test that advanced parameters are identified."""
        for param in ADVANCED_PARAMS:
            group = _get_param_ui_group(param)
            # Some params might be in CORE_PARAMS too (like epsilon)
            assert group in ("core", "advanced")

    def test_extract_params_includes_ui_group(self):
        """Test that extracted params have ui_group."""
        from sklearn.linear_model import Ridge
        
        params = _extract_sklearn_params(Ridge)
        
        for p in params:
            assert hasattr(p, "ui_group")
            assert p.ui_group in ("core", "advanced", "internal")

    def test_extract_params_includes_recommended_range(self):
        """Test that params with recommended ranges are enriched."""
        from sklearn.ensemble import RandomForestRegressor
        
        params = _extract_sklearn_params(RandomForestRegressor)
        n_estimators = next(p for p in params if p.name == "n_estimators")
        
        assert n_estimators.recommended_min == 50
        assert n_estimators.recommended_max == 500

    def test_extract_params_includes_description(self):
        """Test that params have meaningful descriptions."""
        from sklearn.linear_model import Ridge
        
        params = _extract_sklearn_params(Ridge)
        alpha = next(p for p in params if p.name == "alpha")
        
        assert "regularization" in alpha.description.lower()

    def test_extract_params_detects_choices(self):
        """Test that choice params are detected."""
        from sklearn.svm import SVR
        
        params = _extract_sklearn_params(SVR)
        kernel = next(p for p in params if p.name == "kernel")
        
        assert kernel.type == "choice"
        assert "rbf" in kernel.choices


# =============================================================================
# Registry Tests
# =============================================================================


class TestModelRegistry:
    """Tests for the ModelRegistry class."""

    def test_registry_singleton(self):
        """Test that registry is a singleton."""
        r1 = get_model_registry()
        r2 = get_model_registry()
        
        assert r1 is r2

    def test_registry_reset(self):
        """Test that registry can be reset."""
        r1 = get_model_registry()
        ModelRegistry.reset()
        r2 = get_model_registry()
        
        assert r1 is not r2

    def test_registry_list_all_includes_new_fields(self):
        """Test that list_all includes ui_group and recommended ranges."""
        registry = get_model_registry()
        models = registry.list_all()
        
        assert len(models) > 0
        
        # Check that parameters include new fields
        for model in models:
            for param in model["parameters"]:
                assert "ui_group" in param
                assert "recommended_min" in param
                assert "recommended_max" in param

    def test_registry_list_by_category(self):
        """Test filtering models by category."""
        registry = get_model_registry()
        
        linear_models = registry.list_by_category("linear")
        ensemble_models = registry.list_by_category("ensemble")
        
        assert len(linear_models) >= 5
        assert len(ensemble_models) >= 3
        
        for m in linear_models:
            assert m["category"] == "linear"

    def test_registry_get_model(self):
        """Test getting a specific model."""
        registry = get_model_registry()
        
        model = registry.get("linear_regression")
        assert model is not None
        assert model.name == "linear_regression"
        assert model.task_type == "regression"

    def test_registry_get_unknown_model(self):
        """Test that unknown model returns None."""
        registry = get_model_registry()
        
        model = registry.get("nonexistent_model")
        assert model is None


# =============================================================================
# Model Parameter Tests
# =============================================================================


class TestModelParameter:
    """Tests for the ModelParameter dataclass."""

    def test_model_parameter_defaults(self):
        """Test ModelParameter default values."""
        param = ModelParameter(
            name="test",
            display_name="Test",
            type="number",
        )
        
        assert param.required is False
        assert param.default is None
        assert param.ui_group == "advanced"
        assert param.log_scale is False
        assert param.recommended_min is None
        assert param.recommended_max is None

    def test_model_parameter_all_fields(self):
        """Test ModelParameter with all fields."""
        param = ModelParameter(
            name="alpha",
            display_name="Alpha",
            type="number",
            required=False,
            default=1.0,
            description="Regularization strength",
            choices=[],
            min_value=1e-10,
            max_value=None,
            recommended_min=1e-4,
            recommended_max=10.0,
            log_scale=True,
            ui_group="core",
        )
        
        assert param.name == "alpha"
        assert param.ui_group == "core"
        assert param.log_scale is True
        assert param.recommended_min == 1e-4
