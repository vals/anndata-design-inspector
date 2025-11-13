---
name: anndata-design-inspector
description: Inspects and visualizes experimental designs from AnnData .h5ad single-cell data files. Automatically detects species from gene naming patterns, extracts factors (genotypes, samples, cell types), detects design structure (nested vs crossed), generates edviz grammar notation, creates professional visualizations, and produces experiment card documentation. Use when analyzing h5ad files to understand experimental design structure.
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
5. **Detect species** by exploring .var columns and analyzing gene naming patterns
6. **Reason about experimental factors** - understand biological/experimental meaning
7. **Detect design structure** using detect_nesting.sh
8. **Generate edviz grammar** using design_to_grammar.py (**CRITICAL: EVERY experimental factor MUST appear**)
9. **Visualize** the design structure
10. **Generate experiment card** (markdown report documenting the design)
11. **Present results** with clear summary and visualizations

**FUNDAMENTAL RULE FOR GRAMMAR GENERATION:**
Every factor you classify as `"type": "experimental"` in your JSON MUST appear by name in the final grammar string.
- If you have CellFraction (experimental) and DietTimepoint (experimental), the grammar MUST contain both "CellFraction" and "DietTimepoint" (or their CamelCase versions)
- NO EXCEPTIONS: Do not omit factors because they're "encoded in sample names" or "sample-level" - they still must appear
- If you're unsure how factors relate, use `×` (crossing) to connect them: `Factor1 × Factor2 > Sample`

**Important Resources**:
- **GRAMMAR.md**: Full edviz grammar specification with operator semantics, validation rules, and examples
- **Helper scripts**: Located in `$SKILL_DIR/` (list_factors.sh, extract_categories.sh, etc.)
- **Python scripts**: Located in `$SKILL_DIR/scripts/` (check_edviz.py, design_to_grammar.py)

## Step 0: Locate the Skill Directory

CRITICAL: Before doing anything else, locate where the skill scripts are installed. The skill may be installed as a project skill or personal skill.

```bash
# Find the skill directory and expand to full path
if [ -d ".claude/skills/anndata-design-inspector" ]; then
    SKILL_DIR="$(cd .claude/skills/anndata-design-inspector && pwd)"
elif [ -d "$HOME/.claude/skills/anndata-design-inspector" ]; then
    SKILL_DIR="$(cd $HOME/.claude/skills/anndata-design-inspector && pwd)"
else
    echo "Error: Cannot locate anndata-design-inspector skill directory" >&2
    exit 1
fi

echo "Skill directory: $SKILL_DIR"
```

This will output the full absolute path (e.g., `/Users/username/.claude/skills/anndata-design-inspector`).

**IMPORTANT**:
- Store this full path and use it literally in all subsequent commands
- Do NOT use `$SKILL_DIR` or `$HOME` in later commands - use the actual expanded path
- Example: If the output is `/Users/val/.claude/skills/anndata-design-inspector`, then use that exact path in all script calls

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
<SKILL_DIR>/list_factors.sh <file_path>
```

Replace `<SKILL_DIR>` with the actual path from Step 0.

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
python <SKILL_DIR>/scripts/check_edviz.py
```

Replace `<SKILL_DIR>` with the actual path from Step 0.

This script will:
- Check if edviz is already installed
- If not, automatically install it from GitHub (https://github.com/vals/edviz)
- Report success or failure

If installation fails, the skill will continue with basic visualization (without edviz grammar output).

**Grammar Reference**: The full edviz grammar specification is available in `$SKILL_DIR/GRAMMAR.md`. This document contains:
- Formal EBNF grammar definition
- Complete operator semantics and precedence rules
- Factor specification syntax (balanced, unbalanced, approximate)
- Validation rules and constraints
- Extensive examples with parse trees

You can read this file when you need to understand complex grammar constructs or validate edge cases.

### Step 4: Extract Category Information

For each categorical factor found, extract its category names:
```bash
<SKILL_DIR>/extract_categories.sh <file_path> <factor_name>
```

Replace `<SKILL_DIR>` with the actual path from Step 0.

This extracts and cleans the category labels for the specified factor.

### Step 5: Count Cells Per Category

Get cell counts for each category in a factor:
```bash
<SKILL_DIR>/count_cells.sh <file_path> <factor_name>
```

Replace `<SKILL_DIR>` with the actual path from Step 0.

This outputs category:count pairs (e.g., "KeapKO_tumor_1:5103").

To get total cells:
```bash
h5ls <file_path>/obs/_index
```

The number in curly braces `{N}` is the total cell count.

### Step 5a: Detect Species from Gene Names

Identify the organism by examining gene naming patterns in the .var slot.

**Step 5a.1: List available columns in /var**
```bash
h5ls <file_path>/var
```

**Step 5a.2: Sample values from promising columns**

Look for columns that might contain gene identifiers. Prioritize:
- Columns with "symbol", "gene", "name" in the name
- Then try "_index" or "index" columns

For each promising column, extract a sample of ~20 values:
```bash
h5dump -d "/var/<column_name>" <file_path> 2>/dev/null | grep -oE '"[^"]+"' | tr -d '"' | head -20
```

**Step 5a.3: Analyze the samples and infer species**

Look at the case patterns in the gene names:
- **Human**: Uppercase gene names (ACTB, GAPDH, TP53, CD4, CD8A)
- **Mouse**: Title case gene names (Actb, Gapdh, Tp53, Cd4, Cd8a)
- **Zebrafish**: Lowercase gene names (actb, gapdh, tp53, cd4)
- **Drosophila**: Mixed case gene names (Act5C, Gapdh, CG1234)

Examine which pattern is most common across the samples. If the dominant pattern is >50% of genes, report that species. Otherwise report "unknown".

Choose the column with the clearest gene naming pattern (prefer gene symbols over Ensembl IDs or numeric identifiers).

### Step 5b: Reason About Experimental Factors

After identifying all factors, analyze their names and categories to understand the biological/experimental context:

**For each factor, consider:**
1. **What type of experimental manipulation does this represent?**
   - Treatment/drug (e.g., PBS, R848, UNTX, compound names)
   - Genotype/genetic perturbation (e.g., WT, KO, mutation names)
   - Timepoint/temporal dimension (e.g., 0h, 24h, day1, day7)
   - Tissue/organ type (e.g., liver, brain, tumor)
   - Cell line or organism ID
   - Technical batch information
   - **Composite factors** (e.g., DietTimepoint with levels like "HFHS_15weeks", "Chow_52weeks") - note these encode MULTIPLE dimensions

2. **What is the biological/experimental meaning?**
   - Look up unfamiliar terms (e.g., "R848" is a TLR7/8 agonist used to stimulate immune response)
   - Understand the experimental question (e.g., comparing treated vs control, genotype effects, time course)
   - Identify control conditions (PBS, UNTX, WT, vehicle, etc.)

3. **Is this a real experimental factor or a technical identifier?**
   - **Experimental factors** (genotype, treatment, timepoint, tissue) → MUST be in the grammar
   - **Replicates/samples** (sample_1, sample_2, mouse_A, mouse_B) → Include in grammar as nested level
   - **Technical factors** (batch, sequencing_run) → Include if relevant to design
   - **Classification/measurement** (cell_type, cluster, annotation) → Use `:` operator

4. **Does the factor encode multiple experimental dimensions?**
   - Look for patterns like: `ConditionA_Time1`, `ConditionA_Time2`, `ConditionB_Time1`, `ConditionB_Time2`
   - Examples: `DietTimepoint`, `TreatmentDose`, `GenotypeAge`
   - These represent crossing of TWO factors that BOTH must appear in the grammar
   - When building relationships, consider if you should parse into separate factors or keep combined

**Present a brief experimental context summary:**
```
Experimental Context:
This appears to be a [type of experiment] comparing [factors].
- Factor X: [biological meaning and levels]
- Factor Y: [biological meaning and levels]
Research question: [inferred question being addressed]
```

### Step 6: Summarize the Experimental Design

After gathering all the information, present a clear summary:

**Experimental Design Summary:**
- Species: [detected species]
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
Species: Mouse (Mus musculus)
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
<SKILL_DIR>/detect_nesting.sh <file_path> <factor_a> <factor_b>
```

Replace `<SKILL_DIR>` with the actual path from Step 0.

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
- **ALL experimental factors** (treatment, genotype, timepoint, tissue, etc.) MUST be included in the grammar
- Samples/replicates are usually the most specific/nested level
- Biological replicates are nested within experimental conditions
- Cell types are measured variables (use classification `:` operator, not nesting)

**IMPORTANT**: Do NOT exclude experimental factors from the grammar with notes like "treatment is a sample-level factor, not shown". If treatment varies between samples, represent it properly:
- If treatments are crossed with other factors: `Genotype(2) × Treatment(3) > Sample(6)`
- If samples are nested in treatments: `Treatment(3) > Sample(n per treatment)`
- If sample names encode treatment, the treatment factor should still appear explicitly in the grammar

**Common mistake - Timepoints/Diets encoded in sample names:**
If you have factors like `DietTimepoint` with levels like `HFHS_15weeks`, `HFHS_52weeks`, `Chow_15weeks`, `Chow_52weeks`:
- This represents TWO crossed factors: Diet × Timepoint
- WRONG: `Sample(~38) : CellType(13)` (omits both factors)
- RIGHT: `Diet(2) × Timepoint(2) > Sample(~38) : CellType(13)`
- Or if diet/time are combined: `DietTimepoint(4) > Sample(~38) : CellType(13)`

### Step 9: Build Design Hierarchy

Determine the nesting structure from most general to most specific.

**CRITICAL**: All experimental factors MUST be represented. If you have multiple experimental factors:
1. Determine if they are crossed (all combinations exist) or nested (hierarchical)
2. Check if samples are unique to combinations of factors or shared across

**Common patterns**:
- `genotype > sample` (samples nested in genotype)
- `genotype × treatment > sample` (2 factors fully crossed, samples in each combination)
- `treatment > timepoint > sample` (3-level hierarchy)
- `diet × timepoint > sample` (crossed factors, samples in each diet×time combination)
- `batch > genotype × treatment > sample` (mixed: nested + crossed)

**If you have a factor like "DietTimepoint" that encodes multiple dimensions:**
- Option 1: Keep it as one factor: `DietTimepoint(4) > Sample`
- Option 2: Parse it into separate factors: `Diet(2) × Timepoint(2) > Sample`
- Choose based on how the data is actually structured

For the hierarchical structure:
1. Identify the top-level factor (usually: genotype, treatment, condition, batch)
2. Identify which factors are nested within it
3. Continue down to the most specific level (usually samples)

### Step 10: Generate edviz Grammar String

After building the design hierarchy, convert the detected structure to edviz grammar format. This provides a standardized, machine-readable representation of the experimental design.

**CRITICAL PRE-CHECK**: Before generating grammar, verify that ALL factors marked as "experimental" type will be included:
- Review your JSON structure
- List all factors with `"type": "experimental"`
- Each one MUST appear in the grammar string
- If you're unsure how to include a factor, use `×` (crossing) by default rather than omitting it

**CRITICAL CONSTRAINTS** (see GRAMMAR.md for full details):
1. **Classification is terminal**: The `:` operator MUST be the last operation in a chain. You CANNOT have operations after classification.
   - ✅ Valid: `Sample(4) > Cell(5k) : CellType(6)`
   - ❌ Invalid: `Cell(5k) : CellType(6) > Something`
2. **Factor names become CamelCase**: `cell_type` → `CellType`, `time_point` → `TimePoint`
3. **Every factor needs a size spec**: `Factor(n)` for balanced, `Factor[n1|n2|...]` for unbalanced
4. **Operator precedence** (highest to lowest): `()` > `:` > `>` > `×` > `≈≈`
5. **Nesting vs Classification**:
   - Use `>` when child instances are unique to parent (samples nested in genotypes)
   - Use `:` when labeling/categorizing (cells classified into types)
   - Classification does NOT multiply observation counts

**Create a JSON structure** with the detected design information:

**Example 1: Nested design** (samples within genotypes):
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

**Example 2: Factorial crossing** (all combinations exist):
```json
{
  "factors": {
    "genotype": {
      "categories": ["KO", "WT"],
      "counts": [1000, 1000],
      "type": "experimental"
    },
    "timepoint": {
      "categories": ["0h", "24h", "48h"],
      "counts": [666, 667, 667],
      "type": "experimental"
    },
    "cell_type": {
      "categories": ["TypeA", "TypeB"],
      "counts": [1000, 1000],
      "type": "classification"
    }
  },
  "relationships": [
    {"factor": "timepoint", "classifier": "cell_type", "type": "classification"}
  ]
}
```
Note: genotype and timepoint are automatically crossed (no relationship needed) because neither is a child in a nested relationship.

**Example 3: Treatment with samples nested** (different samples per treatment):
```json
{
  "factors": {
    "treatment": {
      "categories": ["PBS", "R848", "UNTX"],
      "counts": [4000, 4000, 4000],
      "type": "experimental"
    },
    "sample": {
      "categories": ["sample_PBS_1", "sample_PBS_2", "sample_R848_1", "sample_R848_2", "sample_UNTX_1", "sample_UNTX_2"],
      "counts": [2000, 2000, 2000, 2000, 2000, 2000],
      "type": "replicate"
    },
    "cell_type": {
      "categories": ["T_cell", "B_cell", "Myeloid"],
      "counts": [4000, 4000, 4000],
      "type": "classification"
    }
  },
  "relationships": [
    {"parent": "treatment", "child": "sample", "type": "nested"},
    {"factor": "sample", "classifier": "cell_type", "type": "classification"}
  ],
  "experimental_context": {
    "experiment_type": "Immune stimulation study",
    "research_question": "How do different immune stimuli affect immune cell populations?",
    "factor_descriptions": {
      "treatment": "Three experimental conditions: PBS (vehicle control), R848 (TLR7/8 agonist for immune stimulation), and UNTX (untreated control)",
      "sample": "Biological replicates (2 per treatment condition)",
      "cell_type": "Major immune cell populations identified by marker expression"
    }
  }
}
```
Grammar: `Treatment(3) > Sample(6) : CellType(3)` or `Treatment(3) > Sample(2) : CellType(3)` depending on balanced replicates

**Factor types**:
- `experimental`: Treatment/condition factors that represent experimental manipulations (genotype, treatment, timepoint, tissue, etc.). These MUST always appear in the grammar.
- `replicate`: Sample/replicate identifiers (often nested within experimental factors)
- `classification`: Measured variables (like cell types) - use with `:` operator
- `batch`: Technical batch effects

**CRITICAL**: All `experimental` type factors MUST be represented in the grammar. Do not exclude them with notes about being "sample-level" or similar. Find the appropriate operator (`×`, `>`) to represent their relationship to other factors.

**Relationship types**:
- `nested`: Hierarchical containment (parent > child). Use when factor B only appears within specific levels of factor A.
- `classification`: Labeling/categorization (factor : classifier). Use for measured variables like cell types.
- **NOTE**: Do NOT specify `crossed` relationships. Factors that are not children in nested relationships are automatically crossed.

**Convert to grammar using the Python script**:

CRITICAL: You MUST use the design_to_grammar.py script to generate the grammar string. Do NOT manually construct grammar strings.

```bash
echo '<json_string>' | python <SKILL_DIR>/scripts/design_to_grammar.py -
```

Replace `<SKILL_DIR>` with the actual path from Step 0.

**Alternative if piping causes issues:**
```bash
cat > /tmp/design.json << 'EOF'
<json_content>
EOF
python <SKILL_DIR>/scripts/design_to_grammar.py /tmp/design.json
```

The script will automatically:
- Convert factor names to CamelCase (required by edviz)
- Detect balanced vs unbalanced designs
- Choose correct operators (>, ×, :)
- Validate grammar constraints

**POST-CHECK after getting grammar string**:
1. Count how many factors with `"type": "experimental"` are in your JSON
2. Verify that each one appears in the grammar string
3. If any are missing, revise your relationships JSON and regenerate
4. Example: If you have CellFraction (experimental) and DietTimepoint (experimental), BOTH must appear in the grammar

This will output a grammar string like:
```
Genotype(2) > Sample(4) : CellType(6)
```

**When to consult GRAMMAR.md**:
- Complex nested + crossed designs (e.g., `Hospital(4) > Patient(15) × Treatment(2)`)
- Confounded factors that should be grouped with `{...}`
- Unbalanced designs with varying counts per branch
- Validation errors from edviz that need interpretation
- Understanding why certain operator combinations are invalid

**IMPORTANT**: The script automatically converts factor names to CamelCase (no spaces). For example:
- `cell_type` → `CellType`
- `time_point` → `TimePoint`
- `batch_id` → `BatchId`

**edviz Grammar Operators**:
- `>` (nesting): Parent(n) > Child(m)
- `×` (crossing): Factor1(n) × Factor2(m)
- `:` (classification): Sample(n) : CellType(m)
- `(n)` balanced counts
- `[n1|n2|n3]` unbalanced counts
- `~nk` approximate large counts (e.g., ~21k cells)

### Step 11: Visualize with edviz

REQUIRED: Use edviz to generate a professional visualization. After getting the grammar string from Step 10, immediately visualize it:

```bash
# Replace GRAMMAR_STRING with the actual grammar from Step 10
python3 -c "
from edviz import ExperimentalDesign
grammar = 'GRAMMAR_STRING_HERE'
design = ExperimentalDesign.from_grammar(grammar)
print(design.ascii_diagram())
"
```

**Example** (if grammar was "Genotype(2) > Sample(4)"):
```bash
python3 -c "
from edviz import ExperimentalDesign
design = ExperimentalDesign.from_grammar('Genotype(2) > Sample(4)')
print(design.ascii_diagram())
"
```

**Expected output**: edviz automatically chooses the appropriate visualization style:
- Nested designs → Tree diagram with hierarchical structure
- Crossed designs → Grid/table layout
- Mixed designs → Combined visualization

**IMPORTANT**: Always use edviz for visualization. It was verified to be installed in Step 3a. Do NOT create manual ASCII trees or custom visualizations.

### Step 11a: Generate Experiment Card

REQUIRED: After generating the edviz visualization, automatically create an experiment card (markdown report) documenting the experimental design. This provides a versioned, shareable record of the design structure.

**Create the input JSON for the experiment card:**

Build a JSON structure containing all the design information collected in previous steps:

```json
{
  "h5ad_file": "<file_path>",
  "species": "<detected_species>",
  "total_cells": <total_cells>,
  "design_type": "<design_type>",
  "edviz_grammar": "<grammar_string_from_step_10>",
  "edviz_diagram": "<ascii_diagram_from_step_11>",
  "experimental_context": {
    "experiment_type": "<inferred experiment type>",
    "research_question": "<inferred research question>",
    "factor_descriptions": {
      "<factor_name>": "<biological/experimental meaning>",
      ...
    }
  },
  "factors": {
    "<factor_name>": {
      "categories": ["cat1", "cat2", ...],
      "counts": [n1, n2, ...],
      "type": "experimental|replicate|classification|batch"
    },
    ...
  },
  "relationships": [
    {"parent": "factor1", "child": "factor2", "type": "nested"},
    {"factor": "factor1", "classifier": "cell_type", "type": "classification"},
    ...
  ],
  "design_notes": ["optional notes about ambiguities"],
  "tool_version": "0.1.0"
}
```

**Generate the experiment card:**

```bash
# Create output filename based on input h5ad file
OUTPUT_FILE="${H5AD_FILE%.h5ad}_experiment_card.md"

# Generate the card
echo '<json_string>' | python <SKILL_DIR>/scripts/generate_experiment_card.py - "$OUTPUT_FILE"
```

Replace `<SKILL_DIR>` with the actual path from Step 0.

The experiment card will be saved alongside the h5ad file with the naming convention: `<filename>_experiment_card.md`

**What the experiment card includes:**
- YAML frontmatter with machine-readable metadata
- Dataset information (file path, date, cell counts)
- Identified factors table
- Design classification (nested/crossed/factorial)
- edviz ASCII diagram
- edviz grammar notation in code block
- Cell distribution summary statistics
- Analysis considerations (design-specific recommendations)
- Design notes (if any ambiguities were detected)

**IMPORTANT**: Always generate the experiment card. This provides documentation that can be version controlled, shared with collaborators, and referenced in publications.

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
CellType Distribution Across Conditions:
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
  Genotype(2) > Sample(4) : CellType(6)

Visualization (generated by edviz):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────────── Design Structure ────────────────────┐
│                                                          │
│ Genotype(2)                                              │
│    ↓                                                     │
│ Sample(4)                                                │
│    :                                                     │
│                                                          │
│ CellType(6)                                              │
│                                                          │
└──────────────────────────────────────────────────────────┘

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
