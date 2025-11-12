# Testing the AnnData Design Inspector Skill

## Option 1: Test Individual Components (Quick)

### Test edviz installation
```bash
python scripts/check_edviz.py
```
Expected output: `✓ edviz is already installed` (or successful installation message)

### Test grammar conversion
```bash
echo '{
  "factors": {
    "genotype": {
      "categories": ["WT", "KO"],
      "counts": [5000, 5000],
      "type": "experimental"
    },
    "sample": {
      "categories": ["WT_1", "WT_2", "KO_1", "KO_2"],
      "counts": [2500, 2500, 2500, 2500],
      "type": "replicate"
    },
    "cell_type": {
      "categories": ["T_cells", "B_cells", "Macrophages"],
      "counts": [3000, 4000, 3000],
      "type": "classification"
    }
  },
  "relationships": [
    {"parent": "genotype", "child": "sample", "type": "nested"},
    {"factor": "sample", "classifier": "cell_type", "type": "classification"}
  ]
}' | python scripts/design_to_grammar.py -
```
Expected output: `Genotype(2) > Sample(4) : CellType(3)`

### Test edviz visualization
```bash
python3 -c "
from edviz import ExperimentalDesign
grammar = 'Genotype(2) > Sample(4) : CellType(3)'
design = ExperimentalDesign.from_grammar(grammar)
print(design.ascii_diagram())
"
```
Expected output: ASCII diagram with design structure

## Option 2: Install and Test End-to-End

### Step 1: Install the skill

**Option A: Install as personal skill**
```bash
# From this directory
mkdir -p ~/.claude/skills
ln -s $(pwd) ~/.claude/skills/anndata-design-inspector
```

**Option B: Install as project skill**
```bash
# In your project directory
mkdir -p .claude/skills
ln -s /Users/val/Documents/Software/claude-skills/anndata-design-inspector .claude/skills/
```

### Step 2: Verify installation
```bash
# Check if skill is linked
ls -la ~/.claude/skills/anndata-design-inspector
# or
ls -la .claude/skills/anndata-design-inspector
```

### Step 3: Test with Claude Code

In Claude Code, try one of these prompts:

**If you have a real .h5ad file:**
```
Can you inspect this h5ad file: /path/to/your/file.h5ad
```

**Test with skill activation:**
```
I have an AnnData h5ad file with single-cell data. Can you show me how to analyze its experimental design?
```

Claude should automatically invoke the `anndata-design-inspector` skill.

## Option 3: Create a Test .h5ad File

If you don't have a real .h5ad file, create a minimal one for testing:

```python
# create_test_h5ad.py
import numpy as np
import pandas as pd
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
adata.write('test_data.h5ad')
print("Created test_data.h5ad")
print(f"Shape: {adata.shape}")
print(f"Obs columns: {list(adata.obs.columns)}")
```

Then run:
```bash
# Install anndata if needed
pip install anndata

# Create test file
python create_test_h5ad.py

# Test with the skill
ls -lh test_data.h5ad
```

Now ask Claude: "Inspect the experimental design in test_data.h5ad"

## Option 4: Manual Step-by-Step Test

Test the workflow manually to verify each step works:

```bash
# Assuming you have a test .h5ad file
FILE="test_data.h5ad"

# Step 1: Check tools
./check_tools.sh

# Step 2: List factors
./list_factors.sh $FILE

# Step 3: Extract categories for each factor
./extract_categories.sh $FILE genotype
./extract_categories.sh $FILE sample
./extract_categories.sh $FILE cell_type

# Step 4: Count cells per factor
./count_cells.sh $FILE genotype
./count_cells.sh $FILE sample

# Step 5: Detect nesting
./detect_nesting.sh $FILE genotype sample
```

## Verification Checklist

- [ ] `check_edviz.py` runs without errors
- [ ] `design_to_grammar.py` converts JSON to valid grammar
- [ ] edviz can parse and visualize the grammar
- [ ] Skill appears in `~/.claude/skills/` or `.claude/skills/`
- [ ] SKILL.md has valid YAML frontmatter with `allowed-tools`
- [ ] Claude automatically invokes the skill when mentioning .h5ad files
- [ ] Helper bash scripts run WITHOUT asking for permission (thanks to `allowed-tools`)
- [ ] Helper bash scripts work with actual .h5ad files
- [ ] Visualization output is readable and informative

## Troubleshooting

**Skill not activating:**
- Check that SKILL.md has YAML frontmatter
- Verify skill is in the correct directory
- Restart Claude Code
- Use explicit trigger words: "h5ad", "AnnData", "experimental design"

**HDF5 tools not found:**
```bash
# macOS
brew install hdf5

# Linux
sudo apt-get install hdf5-tools
```

**edviz installation fails:**
- Check internet connection
- Try manual install: `pip install git+https://github.com/vals/edviz.git`
- Verify Python 3.8+ is installed

**Grammar parsing fails:**
- Check that factor names don't have special characters
- Verify JSON structure matches expected format
- Test with simple example first
