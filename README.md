# AnnData Design Inspector

A Claude Code skill for inspecting and visualizing experimental designs from AnnData `.h5ad` files.

## Overview

This skill uses HDF5 command-line tools (`h5ls` and `h5dump`) to extract experimental design information from single-cell data stored in `.h5ad` format, then visualizes the design structure automatically.

## Files

- **skill.md** - Main skill definition for Claude Code
- **Helper Scripts:**
  - `check_tools.sh` - Check if HDF5 tools are installed
  - `list_factors.sh` - List all categorical factors in a file
  - `extract_categories.sh` - Extract category names from a factor
  - `count_cells.sh` - Count cells per category
  - `detect_nesting.sh` - Detect if factors are nested or crossed

## Prerequisites

HDF5 command-line tools (`h5ls` and `h5dump`) must be installed:

**macOS:**
```bash
brew install hdf5
```

**Linux (Debian/Ubuntu):**
```bash
sudo apt-get install hdf5-tools
```

**Check installation:**
```bash
./check_tools.sh
```

## Helper Scripts Usage

### check_tools.sh
Check if HDF5 tools are installed, optionally install them:
```bash
./check_tools.sh              # Check only
./check_tools.sh --install    # Install if missing
```

### list_factors.sh
List all categorical factors (Groups) in the obs section:
```bash
./list_factors.sh <h5ad_file>
```

Example:
```bash
./list_factors.sh data.h5ad
# Output:
# cell_type
# genotype
# sample
```

### extract_categories.sh
Extract category names from a specific factor:
```bash
./extract_categories.sh <h5ad_file> <factor_name>
```

Example:
```bash
./extract_categories.sh data.h5ad genotype
# Output:
# KeapKO
# KeapWT
```

### count_cells.sh
Count how many cells belong to each category:
```bash
./count_cells.sh <h5ad_file> <factor_name>
```

Example:
```bash
./count_cells.sh data.h5ad sample
# Output:
# KeapKO_tumor_1:5103
# KeapKO_tumor_2:3881
# KeapWT_tumor_1:7904
# KeapWT_tumor_2:4537
```

### detect_nesting.sh
Detect if factor B is nested within factor A or if they're crossed:
```bash
./detect_nesting.sh <h5ad_file> <factor_a> <factor_b>
```

Example:
```bash
./detect_nesting.sh data.h5ad genotype sample
# Output:
# nested
```

## Using the Skill

The skill automatically:
1. Validates the .h5ad file
2. Identifies all experimental factors
3. Extracts categories and cell counts
4. Detects design structure (nested vs crossed)
5. Renders appropriate visualizations (tree for nested, grid for crossed)
6. Shows cell count distributions

## Example Output

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

Design Structure: Hierarchical (Nested)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

                    Experimental Design
                            │
                ┌───────────┴───────────┐
             KeapKO                  KeapWT
           (n=8,984)               (n=12,441)
                │                       │
          ┌─────┴─────┐           ┌─────┴─────┐
      tumor_1     tumor_2      tumor_1     tumor_2
    (n=5,103)   (n=3,881)    (n=7,904)   (n=4,537)
```

## Design Types Supported

- **Nested/Hierarchical**: Samples nested within conditions
- **Crossed/Factorial**: All combinations of factors exist
- **Mixed**: Combination of nested and crossed factors

## Development

To add new features:
1. Update `skill.md` with new instructions
2. Create helper scripts for complex operations
3. Test with various .h5ad file structures

## License

MIT
