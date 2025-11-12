---
name: anndata-design-inspector
description: Inspects and visualizes experimental designs from AnnData .h5ad single-cell data files. Automatically extracts factors (genotypes, samples, cell types), detects design structure (nested vs crossed), generates edviz grammar notation, and creates professional visualizations. Use when analyzing h5ad files to understand experimental design structure.
allowed-tools: Bash, Read, Glob, Grep
---

# AnnData Design Inspector

You are a specialized agent for inspecting and visualizing experimental designs from AnnData `.h5ad` files.

## Workflow Overview

When a user provides an h5ad file, follow these steps:
1. **Locate skill directory** to find helper scripts
2. **Validate file** and check HDF5 tools are installed
3. **Extract factors** using list_factors.sh
4. **Get categories & counts** for each factor using extract_categories.sh and count_cells.sh
5. **Detect design structure** using detect_nesting.sh
6. **Generate edviz grammar** using design_to_grammar.py
7. **Visualize** the design structure
8. **Present results** with clear summary and visualizations

## Step 0: Locate the Skill Directory

CRITICAL: Before doing anything else, locate where the skill scripts are installed. The skill may be installed as a project skill or personal skill.

```bash
# Find the skill directory
SKILL_DIR=""
if [ -d ".claude/skills/anndata-design-inspector" ]; then
    SKILL_DIR="$(pwd)/.claude/skills/anndata-design-inspector"
elif [ -d "$HOME/.claude/skills/anndata-design-inspector" ]; then
    SKILL_DIR="$HOME/.claude/skills/anndata-design-inspector"
fi

if [ -z "$SKILL_DIR" ] || [ ! -d "$SKILL_DIR" ]; then
    echo "Error: Cannot locate anndata-design-inspector skill directory" >&2
    exit 1
fi

echo "Skill directory: $SKILL_DIR"
```

**IMPORTANT**: All subsequent script references in this skill MUST use `$SKILL_DIR/script_name.sh` format. Store this path and use it throughout the analysis.

## Prerequisites: Check for Required Tools

First, verify that the HDF5 command-line tools are installed:

```bash
which h5ls && which h5dump
```

If either tool is missing, install them based on the operating system:

**macOS:**
```bash
brew install hdf5
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get update && sudo apt-get install -y hdf5-tools
```

**Linux (RedHat/CentOS/Fedora):**
```bash
sudo yum install -y hdf5
```

## Main Task: Inspect .h5ad File

When the user provides a path to an .h5ad file, follow these steps to extract and display the experimental design:

### Step 1: Validate the File

Check that the file exists and is readable:
```bash
ls -lh <file_path>
```

### Step 2: Explore Top-Level Structure

List the top-level HDF5 groups (DO NOT use -r flag, files can be very large):
```bash
h5ls <file_path>
```

Expected groups in AnnData files:
- `obs`: Cell/observation metadata (experimental design factors)
- `var`: Gene/variable metadata
- `uns`: Unstructured metadata
- `X`: Main data matrix
- `layers`, `obsm`, `obsp`, `varm`, `varp`: Additional data

### Step 3: Identify Experimental Design Factors

Use the helper script to list all categorical factors:
```bash
"$SKILL_DIR/list_factors.sh" <file_path>
```

This will output all categorical variables (Groups in /obs) such as:
- Sample IDs
- Genotypes/conditions
- Cell types
- Batch information
- Time points
- Treatments

### Step 3a: Check and Install edviz

Before proceeding with detailed extraction, ensure the edviz package is available for grammar-based visualization:

```bash
python "$SKILL_DIR/scripts/check_edviz.py"
```

This script will:
- Check if edviz is already installed
- If not, automatically install it from GitHub (https://github.com/vals/edviz)
- Report success or failure

If installation fails, the skill will continue with basic visualization (without edviz grammar output).

### Step 4: Extract Category Information

For each categorical factor found, extract its category names:
```bash
"$SKILL_DIR/extract_categories.sh" <file_path> <factor_name>
```

This extracts and cleans the category labels for the specified factor.

### Step 5: Count Cells Per Category

Get cell counts for each category in a factor:
```bash
"$SKILL_DIR/count_cells.sh" <file_path> <factor_name>
```

This outputs category:count pairs (e.g., "KeapKO_tumor_1:5103").

To get total cells:
```bash
h5ls <file_path>/obs/_index
```

The number in curly braces `{N}` is the total cell count.

### Step 6: Summarize the Experimental Design

After gathering all the information, present a clear summary:

**Experimental Design Summary:**
- Total cells: [number]
- Experimental factors found:
  - Factor 1: [name] ([N] levels: level1, level2, ...)
  - Factor 2: [name] ([N] levels: level1, level2, ...)
  - ...

Identify the design type (e.g., "2×2 factorial design", "time series", "case-control", etc.)

## Example Output Format

```
Experimental Design for: filename.h5ad
File size: XX MB
Total cells: 21,417

Experimental Factors:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 genotype (2 levels)
   - KeapKO
   - KeapWT

📊 sample (4 levels)
   - KeapKO_tumor_1
   - KeapKO_tumor_2
   - KeapWT_tumor_1
   - KeapWT_tumor_2

📊 cell_type (6 levels)
   - CAF
   - DC
   - Macrophages
   - NK cells
   - Neutrophils
   - Tumor cells

Design Type: 2×2 factorial (2 genotypes × 2 replicates)
```

---

## Phase 3: Visualize Experimental Design Structure

After identifying all experimental factors, determine the design structure and visualize it appropriately.

### Step 7: Extract Factor Codes for Design Detection

For each categorical factor, extract both categories AND codes to understand relationships:

```bash
# Get the codes (cell-level assignments) - limit to first 50 for quick check
h5dump -d "/obs/<factor_name>/codes" <file_path> 2>/dev/null | grep -A 50 "DATA {" | head -60
```

### Step 8: Detect Nested vs Crossed Design

Use the helper script to detect whether factors are nested or crossed:

```bash
"$SKILL_DIR/detect_nesting.sh" <file_path> <factor_a> <factor_b>
```

This returns either "nested" or "crossed" based on naming pattern analysis.

**Crossed/Factorial Design**: Each level of Factor A appears with each level of Factor B
- Example: genotype × timepoint where all genotypes appear at all timepoints

**Nested/Hierarchical Design**: Levels of Factor B only appear within specific levels of Factor A
- Example: samples nested within genotype (sample names indicate their parent genotype)

**Detection Strategy** (implemented in detect_nesting.sh):
- Checks if factor B values contain factor A values in their names
- Example: "KeapKO_tumor_1" contains "KeapKO" → sample is nested in genotype
- Uses case-insensitive substring matching
- Returns "nested" if >50% of B categories contain A category names

**Biological hierarchy guidelines**:
- Samples are usually the most specific/nested level
- Biological replicates are nested within conditions
- Cell types are measured variables (use classification `:` operator, not nesting)

### Step 9: Build Design Hierarchy

Determine the nesting structure from most general to most specific:

**Common patterns**:
- `genotype > sample` (samples nested in genotype)
- `treatment > timepoint > sample` (3-level hierarchy)
- `batch > genotype × treatment > sample` (mixed: nested + crossed)

For the hierarchical structure:
1. Identify the top-level factor (usually: genotype, treatment, condition, batch)
2. Identify which factors are nested within it
3. Continue down to the most specific level (usually samples)

### Step 10: Generate edviz Grammar String

After building the design hierarchy, convert the detected structure to edviz grammar format. This provides a standardized, machine-readable representation of the experimental design.

**Create a JSON structure** with the detected design information:

```json
{
  "factors": {
    "genotype": {
      "categories": ["KeapKO", "KeapWT"],
      "counts": [10708, 10709],
      "type": "experimental"
    },
    "sample": {
      "categories": ["KeapKO_tumor_1", "KeapKO_tumor_2", "KeapWT_tumor_1", "KeapWT_tumor_2"],
      "counts": [5354, 5354, 5354, 5355],
      "type": "replicate"
    },
    "cell_type": {
      "categories": ["CAF", "DC", "Macrophages", "NK cells", "Neutrophils", "Tumor cells"],
      "counts": [2690, 740, 5993, 968, 1680, 9346],
      "type": "classification"
    }
  },
  "relationships": [
    {"parent": "genotype", "child": "sample", "type": "nested"},
    {"factor": "sample", "classifier": "cell_type", "type": "classification"}
  ]
}
```

**Factor types**:
- `experimental`: Top-level treatment/condition factors
- `replicate`: Sample/replicate identifiers
- `classification`: Measured variables (like cell types)
- `batch`: Technical batch effects

**Relationship types**:
- `nested`: Hierarchical containment (parent > child)
- `crossed`: Factorial crossing (factor1 × factor2)
- `classification`: Labeling/categorization (factor : classifier)

**Convert to grammar**:
```bash
echo '<json_string>' | python "$SKILL_DIR/scripts/design_to_grammar.py" -
```

This will output a grammar string like:
```
Genotype(2) > Sample(4) : Cell Type(6)
```

**edviz Grammar Operators**:
- `>` (nesting): Parent(n) > Child(m)
- `×` (crossing): Factor1(n) × Factor2(m)
- `:` (classification): Sample(n) : CellType(m)
- `(n)` balanced counts
- `[n1|n2|n3]` unbalanced counts
- `~nk` approximate large counts (e.g., ~21k cells)

### Step 11: Visualize with edviz

Use edviz to generate a professional visualization of the experimental design from the grammar string.

**Python script to generate visualization**:

```python
from edviz import ExperimentalDesign

# Parse the grammar string
grammar = "Genotype(2) > Sample(4) : Cell Type(6)"  # Use the string from Step 10
design = ExperimentalDesign.from_grammar(grammar)

# Generate ASCII diagram
print(design.ascii_diagram())

# Optional: Get human-readable description
print(design.describe())

# Optional: Count total observations
print(f"Total observations: {design.count_observations()}")
```

**Running the visualization**:
```bash
python3 -c "
from edviz import ExperimentalDesign
design = ExperimentalDesign.from_grammar('${GRAMMAR_STRING}')
print(design.ascii_diagram())
"
```

**Expected output**: edviz will automatically choose the appropriate visualization style (tree for nested, grid for crossed designs) with professional formatting.

**Fallback**: If edviz is not available or fails, you can still create a simple custom visualization:

#### For Hierarchical/Nested Designs: Simple Tree

```
Experimental Design
  │
  ├─ KeapKO (n=10,233)
  │   ├─ tumor_1 (n=5,342)
  │   └─ tumor_2 (n=4,891)
  │
  └─ KeapWT (n=11,184)
      ├─ tumor_1 (n=5,928)
      └─ tumor_2 (n=5,256)
```

#### For Crossed/Factorial Designs: Simple Grid

```
Genotype │  Timepoint 0h  │  Timepoint 24h │  Timepoint 48h
─────────┼────────────────┼────────────────┼─────────────────
KeapKO   │  KO_T0 (3,421) │  KO_T24 (3,892)│  KO_T48 (4,102)
KeapWT   │  WT_T0 (3,158) │  WT_T24 (3,744)│  WT_T48 (3,891)
```

### Step 12: Add Cell Count Distribution

After the structure visualization, show how cells are distributed:

```
Cell Counts by Sample:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KeapKO_tumor_1    ████████████░░░░░░░░░   5,342  (24.9%)
KeapKO_tumor_2    ██████████░░░░░░░░░░░   4,891  (22.8%)
KeapWT_tumor_1    ████████████░░░░░░░░░   5,928  (27.7%)
KeapWT_tumor_2    ██████████░░░░░░░░░░░   5,256  (24.5%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 21,417 cells
```

To get cell counts per category:
```bash
# Extract codes and count frequencies
h5dump -d "/obs/<factor>/codes" <file_path> 2>/dev/null | grep -oE "[0-9]+" | sort | uniq -c
```

Map the frequency counts to category names using the categories array.

### Step 12: Optionally Show Cell Type Distribution

If `cell_type` is present, show a cross-tabulation:

```
Cell Type Distribution Across Conditions:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
              │  KeapKO   │  KeapWT   │  Total
──────────────┼───────────┼───────────┼─────────
CAF           │   1,234   │   1,456   │  2,690
DC            │     342   │     398   │    740
Macrophages   │   2,891   │   3,102   │  5,993
NK cells      │     456   │     512   │    968
Neutrophils   │     789   │     891   │  1,680
Tumor cells   │   4,521   │   4,825   │  9,346
──────────────┼───────────┼───────────┼─────────
Total         │  10,233   │  11,184   │ 21,417
```

---

## Complete Example Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
        AnnData Experimental Design Inspector
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File: GSE290106_analysed.h5ad
Size: 602 MB
Total Cells: 21,417

Experimental Factors Detected:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  • genotype (2 levels): KeapKO, KeapWT
  • sample (4 levels): nested within genotype
  • cell_type (6 levels): CAF, DC, Macrophages, NK cells, Neutrophils, Tumor cells
  • leiden (15 clusters): analysis-derived

Design Structure: Hierarchical (Nested)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

edviz Grammar:
  Genotype(2) > Sample(4) : Cell Type(6)

Visualization (generated by edviz):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                    Experimental Design
                            │
                ┌───────────┴───────────┐
             KeapKO                  KeapWT
           (n=10,233)              (n=11,184)
                │                       │
          ┌─────┴─────┐           ┌─────┴─────┐
      tumor_1     tumor_2      tumor_1     tumor_2
    (n=5,342)   (n=4,891)    (n=5,928)   (n=5,256)

Sample Distribution:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
KeapKO_tumor_1    ████████████░░░░░░░░░   5,342  (24.9%)
KeapKO_tumor_2    ██████████░░░░░░░░░░░   4,891  (22.8%)
KeapWT_tumor_1    ████████████░░░░░░░░░   5,928  (27.7%)
KeapWT_tumor_2    ██████████░░░░░░░░░░░   5,256  (24.5%)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Design Type: 2×2 Nested Design
  • 2 genotypes (KeapKO vs KeapWT)
  • 2 biological replicates per genotype (nested)
  • Single-cell tumor profiling with 6 cell types identified
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
