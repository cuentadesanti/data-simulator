# Determinism Testing

## Overview

The `test_determinism_golden.py` file contains comprehensive tests for ensuring deterministic data generation in the Data Simulator. These tests verify the core invariant:

```
same DAG (canonicalized) + same seed + same sample_size => byte-identical output
```

## Golden Hash Tests

Golden hash tests use pre-computed SHA256 hashes of CSV output as regression tests. If any test fails, it indicates a backward-incompatible change in the generation logic.

### Test Coverage

1. **Golden Hash Fixtures** - Tests with known expected hashes:
   - Simple normal distribution
   - Simple categorical distribution
   - Complex DAG with lookup parameters
   - Comprehensive DAG with all features (categorical, lookups, formulas, scopes, post-processing)

2. **Cross-Run Determinism** - Tests that verify identical output across multiple runs:
   - Simple DAGs
   - Complex DAGs with lookups
   - All scope types (global, group, row)

3. **Topological Order Invariance** - Tests that node order doesn't affect output:
   - Shuffled node orderings
   - Random shuffles

4. **Post-Processing Determinism** - Tests for deterministic post-processing:
   - Clipping
   - Rounding
   - Missing value generation
   - Combined post-processing

5. **Context Determinism** - Tests for deterministic lookup/mapping resolution:
   - LookupValue
   - MappingValue

6. **Edge Cases** - Tests for edge case determinism:
   - Single row
   - Large datasets
   - Many nodes

## Regenerating Golden Hashes

When you make intentional changes to the generation logic, you'll need to update the golden hashes. Follow these steps:

### Option 1: Using the Helper Script

1. Run the hash generation script:
   ```bash
   cd backend
   python generate_golden_hashes.py
   ```

2. The script will output the new hashes. Copy them into the `GOLDEN_HASHES` dictionary in `tests/test_determinism_golden.py`.

3. Verify the tests pass:
   ```bash
   pytest tests/test_determinism_golden.py -v
   ```

### Option 2: Using the Helper Test

1. Edit `tests/test_determinism_golden.py` and comment out the `@pytest.mark.skip` decorator on the `test_generate_golden_hashes` function.

2. Run the helper test:
   ```bash
   pytest tests/test_determinism_golden.py::test_generate_golden_hashes -v -s
   ```

3. Copy the printed hashes into the `GOLDEN_HASHES` dictionary.

4. Re-enable the skip decorator.

5. Verify the tests pass:
   ```bash
   pytest tests/test_determinism_golden.py -v
   ```

## Understanding Hash Failures

When a golden hash test fails, it means one of these things:

1. **Intentional Change**: You've made a deliberate change to the generation algorithm
   - Action: Regenerate golden hashes and update the test file

2. **Unintentional Bug**: You've introduced a bug that breaks determinism
   - Action: Fix the bug to restore deterministic behavior

3. **Platform Difference**: Different platforms may produce slightly different floating-point results
   - Action: Investigate and ensure cross-platform determinism

## Best Practices

1. **Always run determinism tests** before committing changes to sampling logic
2. **Document any intentional changes** that require updating golden hashes in your commit message
3. **Verify cross-platform** determinism when possible (test on different OS/architectures)
4. **Add new test cases** when adding new features to the simulator

## Test Execution

Run all determinism tests:
```bash
pytest tests/test_determinism_golden.py -v
```

Run a specific test class:
```bash
pytest tests/test_determinism_golden.py::TestGoldenHashes -v
```

Run a specific test:
```bash
pytest tests/test_determinism_golden.py::TestGoldenHashes::test_simple_normal_golden_hash -v
```

## Hash Computation

Hashes are computed using SHA256 of the DataFrame serialized to CSV with these settings:
- No index column
- UTF-8 encoding
- Unix line endings (`\n`)
- Deterministic column order (sorted alphabetically)

This ensures byte-identical comparison across different environments.
