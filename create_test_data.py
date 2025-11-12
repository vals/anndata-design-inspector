#!/usr/bin/env python3
"""Create a minimal test .h5ad file for testing the skill."""

import numpy as np
import pandas as pd

try:
    import anndata as ad
except ImportError:
    print("Installing anndata...")
    import subprocess
    subprocess.run(["pip", "install", "anndata"], check=True)
    import anndata as ad

# Create minimal test data
n_obs = 1000
n_vars = 100

# Create random expression data
X = np.random.negative_binomial(5, 0.3, (n_obs, n_vars))

# Create observation metadata (cell-level)
obs = pd.DataFrame({
    'genotype': pd.Categorical(['WT'] * 500 + ['KO'] * 500),
    'sample': pd.Categorical(
        ['WT_rep1'] * 250 + ['WT_rep2'] * 250 +
        ['KO_rep1'] * 250 + ['KO_rep2'] * 250
    ),
    'cell_type': pd.Categorical(
        np.random.choice(['T_cells', 'B_cells', 'Macrophages'], n_obs)
    )
}, index=[f'cell_{i}' for i in range(n_obs)])

# Create variable metadata (gene-level)
var = pd.DataFrame(
    index=[f'gene_{i}' for i in range(n_vars)]
)

# Create AnnData object
adata = ad.AnnData(X=X, obs=obs, var=var)

# Save as h5ad
output_file = 'test_experiment.h5ad'
adata.write(output_file)

print(f"✓ Created {output_file}")
print(f"  Shape: {adata.shape} (cells × genes)")
print(f"  Factors: {list(adata.obs.columns)}")
print(f"  File size: {adata.X.nbytes / 1024:.1f} KB")
print()
print("Ready to test! Try asking:")
print(f'  "Inspect the experimental design in {output_file}"')
