#!/usr/bin/env python3
"""
End-to-End test script for the versioned pipeline and modeling feature.

This script demonstrates the complete workflow:
1. Create a project with a DAG
2. Create a pipeline from the simulation
3. Add transform steps (formula, log, etc.)
4. Materialize the pipeline data
5. Fit ML models (linear regression, logistic regression)
6. Generate predictions

Run with: python scripts/e2e_pipeline_test.py
"""

import json
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.database import Base
from app.db.models import DAGVersion, ModelFit, Pipeline, PipelineVersion, Project
from app.services.modeling_service import fit_model, predict
from app.services.pipeline_service import add_step, create_pipeline, materialize


def main():
    """Run the end-to-end pipeline test."""
    print("=" * 80)
    print("E2E Pipeline & Modeling Test")
    print("=" * 80)
    
    # Create in-memory database
    print("\n[1/8] Setting up test database...")
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        # Step 1: Create a project with a DAG
        print("\n[2/8] Creating project with sample DAG...")
        project = Project(name="E2E Test Project", description="Testing pipeline features")
        db.add(project)
        db.flush()
        
        # Create a simple DAG with income and age
        dag_definition = {
            "schema_version": "1.0",
            "nodes": [
                {
                    "id": "node_income",
                    "name": "income",
                    "kind": "stochastic",
                    "dtype": "float",
                    "scope": "row",
                    "distribution": {"type": "normal", "params": {"mu": 50000, "sigma": 15000}},
                },
                {
                    "id": "node_age",
                    "name": "age",
                    "kind": "stochastic",
                    "dtype": "int",
                    "scope": "row",
                    "distribution": {"type": "uniform", "params": {"low": 22, "high": 65}},
                },
                {
                    "id": "node_education",
                    "name": "education",
                    "kind": "stochastic",
                    "dtype": "int",
                    "scope": "row",
                    "distribution": {"type": "uniform", "params": {"low": 10, "high": 20}},
                },
            ],
            "edges": [],
            "context": {},
            "metadata": {"sample_size": 500, "seed": 42, "preview_rows": 10},
        }
        
        dag_version = DAGVersion(
            project_id=project.id,
            version_number=1,
            dag_definition=dag_definition,
            is_current=True,
        )
        db.add(dag_version)
        db.commit()
        print(f"✓ Created project '{project.name}' with DAG version {dag_version.version_number}")
        
        # Step 2: Create a pipeline from the simulation
        print("\n[3/8] Creating pipeline from simulation...")
        pipeline_result = create_pipeline(
            db=db,
            project_id=project.id,
            name="Income Analysis Pipeline",
            source_type="simulation",
            dag_version_id=dag_version.id,
            seed=42,
            sample_size=500,
        )
        
        pipeline_id = pipeline_result["pipeline_id"]
        version_id = pipeline_result["version_id"]
        print(f"✓ Created pipeline with ID: {pipeline_id[:8]}...")
        print(f"  Initial schema: {[col['name'] for col in pipeline_result['schema']]}")
        
        # Step 3: Add transform steps
        print("\n[4/8] Adding transform steps...")
        
        # Add log transform for income
        step1_result = add_step(
            db=db,
            pipeline_id=pipeline_id,
            version_id=version_id,
            step_spec={
                "type": "log",
                "output_column": "log_income",
                "params": {"column": "income"},
            },
            preview_limit=5,
        )
        version_id = step1_result["new_version_id"]
        print(f"✓ Added 'log' transform → log_income")
        print(f"  Warnings: {step1_result['warnings']}")
        
        # Add formula transform
        step2_result = add_step(
            db=db,
            pipeline_id=pipeline_id,
            version_id=version_id,
            step_spec={
                "type": "formula",
                "output_column": "income_per_year_of_education",
                "params": {"expression": "income / education"},
            },
            preview_limit=5,
        )
        version_id = step2_result["new_version_id"]
        print(f"✓ Added 'formula' transform → income_per_year_of_education")
        
        # Add another formula
        step3_result = add_step(
            db=db,
            pipeline_id=pipeline_id,
            version_id=version_id,
            step_spec={
                "type": "formula",
                "output_column": "age_squared",
                "params": {"expression": "age ** 2"},
            },
            preview_limit=5,
        )
        version_id = step3_result["new_version_id"]
        print(f"✓ Added 'formula' transform → age_squared")
        
        # Add sqrt transform
        step4_result = add_step(
            db=db,
            pipeline_id=pipeline_id,
            version_id=version_id,
            step_spec={
                "type": "sqrt",
                "output_column": "sqrt_income",
                "params": {"column": "income"},
            },
            preview_limit=5,
        )
        version_id = step4_result["new_version_id"]
        print(f"✓ Added 'sqrt' transform → sqrt_income")
        
        final_schema = step4_result["schema"]
        print(f"\n  Final schema ({len(final_schema)} columns):")
        for col in final_schema:
            print(f"    - {col['name']} ({col['dtype']})")
        
        # Step 4: Materialize the pipeline
        print("\n[5/8] Materializing pipeline data...")
        materialized = materialize(
            db=db,
            pipeline_id=pipeline_id,
            version_id=version_id,
            limit=10,
        )
        print(f"✓ Materialized {len(materialized['rows'])} rows")
        print(f"  Sample row:")
        if materialized['rows']:
            sample = materialized['rows'][0]
            for key, value in list(sample.items())[:5]:
                print(f"    {key}: {value}")
        
        # Step 5: Fit a linear regression model
        print("\n[6/8] Fitting linear regression model...")
        model1_result = fit_model(
            db=db,
            pipeline_version_id=version_id,
            name="Income Predictor",
            model_name="linear_regression",
            target="income",
            features=["age", "education", "age_squared"],
            model_params={"fit_intercept": True},
            split_spec={"type": "random", "test_size": 0.2, "random_state": 42},
        )
        
        model1_id = model1_result["model_id"]
        print(f"✓ Fitted linear regression model: {model1_id[:8]}...")
        print(f"  Metrics:")
        for metric, value in model1_result["metrics"].items():
            print(f"    {metric}: {value:.4f}")
        
        if model1_result["coefficients"]:
            print(f"  Coefficients:")
            for name, coef in list(model1_result["coefficients"].items())[:5]:
                print(f"    {name}: {coef:.4f}")
        
        # Step 6: Create a new feature and fit ridge regression
        print("\n[7/8] Adding feature and fitting ridge regression...")
        
        # Add a formula to create a combined feature
        step5_result = add_step(
            db=db,
            pipeline_id=pipeline_id,
            version_id=version_id,
            step_spec={
                "type": "formula",
                "output_column": "age_income_ratio",
                "params": {"expression": "age / income"},
            },
            preview_limit=5,
        )
        version_id = step5_result["new_version_id"]
        print(f"✓ Added feature 'age_income_ratio'")
        
        # Fit ridge regression
        model2_result = fit_model(
            db=db,
            pipeline_version_id=version_id,
            name="Alternative Predictor",
            model_name="ridge",
            target="income",
            features=["age", "education", "log_income"],
            model_params={"alpha": 0.5},
            split_spec={"type": "random", "test_size": 0.2, "random_state": 42},
        )
        
        model2_id = model2_result["model_id"]
        print(f"✓ Fitted ridge regression model: {model2_id[:8]}...")
        print(f"  Metrics:")
        for metric, value in model2_result["metrics"].items():
            print(f"    {metric}: {value:.4f}")
        
        # Step 7: Generate predictions
        print("\n[8/8] Generating predictions...")
        predictions = predict(
            db=db,
            model_id=model1_id,
            pipeline_version_id=version_id,
            limit=5,
        )
        
        print(f"✓ Generated {len(predictions['predictions'])} predictions")
        print(f"  Sample predictions:")
        for i, pred in enumerate(predictions['predictions'][:3]):
            print(f"    Row {i}: {pred:.2f}")
        
        # Verify database state
        print("\n" + "=" * 80)
        print("Database State Summary")
        print("=" * 80)
        
        pipeline_count = db.query(Pipeline).count()
        version_count = db.query(PipelineVersion).count()
        model_count = db.query(ModelFit).count()
        
        print(f"Pipelines: {pipeline_count}")
        print(f"Pipeline Versions: {version_count}")
        print(f"Model Fits: {model_count}")
        
        # Get the final pipeline
        final_pipeline = db.query(Pipeline).filter_by(id=pipeline_id).first()
        final_version = db.query(PipelineVersion).filter_by(id=version_id).first()
        
        print(f"\nFinal Pipeline:")
        print(f"  Name: {final_pipeline.name}")
        print(f"  Current Version: {final_version.version_number}")
        print(f"  Steps: {len(final_version.steps)}")
        print(f"  Output Columns: {len(final_version.output_schema)}")
        
        print(f"\nStep Details:")
        for step in final_version.steps:
            print(f"  {step['order']}. {step['type']} → {step['output_column']}")
        
        print("\n" + "=" * 80)
        print("✅ E2E Test PASSED - All operations completed successfully!")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ E2E Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
