#!/usr/bin/env python3
"""
Generate an experiment card (markdown report) for an h5ad experimental design.

Takes JSON input describing the design structure, edviz grammar, and visualization,
and outputs a markdown experiment card documenting the design.

Usage:
    python scripts/generate_experiment_card.py <input.json> <output.md>
    echo '{"factors": {...}, ...}' | python scripts/generate_experiment_card.py - output.md

Input JSON format:
{
  "h5ad_file": "path/to/file.h5ad",
  "total_cells": 12500,
  "design_type": "nested",
  "edviz_grammar": "Genotype(2) > Sample(4) : CellType(6)",
  "edviz_diagram": "ASCII diagram from edviz",
  "factors": {
    "genotype": {
      "categories": ["KO", "WT"],
      "counts": [6000, 6500],
      "type": "experimental"
    },
    ...
  },
  "relationships": [
    {"parent": "genotype", "child": "sample", "type": "nested"},
    ...
  ],
  "design_notes": ["optional notes about ambiguities or assumptions"]
}
"""

import json
import sys
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
import statistics


def to_title_case(name: str) -> str:
    """Convert factor name to Title Case for display."""
    return name.replace('_', ' ').title()


def format_number(n: int) -> str:
    """Format number with thousands separator."""
    return f"{n:,}"


def get_factor_display_type(factor_type: str) -> str:
    """Get human-readable factor type."""
    type_map = {
        "experimental": "Treatment",
        "replicate": "Replicate",
        "classification": "Observation",
        "batch": "Batch"
    }
    return type_map.get(factor_type, "Factor")


def calculate_summary_stats(counts: List[int]) -> Dict[str, Any]:
    """Calculate summary statistics for a list of counts."""
    if not counts:
        return {"min": 0, "max": 0, "mean": 0, "median": 0}

    return {
        "min": min(counts),
        "max": max(counts),
        "mean": int(statistics.mean(counts)),
        "median": int(statistics.median(counts))
    }


def format_range(stats: Dict[str, Any]) -> str:
    """Format a range with mean for display."""
    if stats["min"] == stats["max"]:
        return f"{format_number(stats['min'])}"
    return f"{format_number(stats['min'])} - {format_number(stats['max'])} (mean: {format_number(stats['mean'])})"


def generate_analysis_section(design_type: str, factors: Dict[str, Any],
                              relationships: List[Dict[str, str]]) -> str:
    """Generate the Analysis Considerations section based on design type."""

    # Find nested relationships
    nested_rels = [r for r in relationships if r.get("type") == "nested"]
    classification_rels = [r for r in relationships if r.get("type") == "classification"]

    content = "This design structure has implications for statistical analysis:\n\n"

    if nested_rels:
        # Handle nested designs
        parent = nested_rels[0].get("parent", "")
        child = nested_rels[0].get("child", "")

        content += f"**Random Effects Modeling:** The nesting of `{child}` within `{parent}` indicates that {child}-specific variation should be modeled as a random effect. When testing for {parent} effects, use mixed-effects models with random intercepts for {child} (e.g., `~ {parent} + (1|{child})` in lme4 notation).\n\n"

        if classification_rels:
            classifier = classification_rels[0].get("classifier", "")
            content += f"**Aggregation Strategy:** For differential expression testing, pseudobulking to the {child} level preserves the experimental unit structure. Aggregate cells to {child}-by-{classifier} pseudobulk profiles before applying standard DE methods, treating {child}s as biological replicates.\n\n"
        else:
            content += f"**Aggregation Strategy:** For differential expression testing, pseudobulking to the {child} level preserves the experimental unit structure. Aggregate cells to the {child} level before applying standard DE methods.\n\n"

        content += f"**Contrast Specification:** When comparing {parent}s, ensure contrasts are computed at the {child} level, not the cell level, to avoid pseudoreplication and inflated Type I error rates."

    elif "crossed" in design_type.lower() or "×" in design_type:
        # Handle crossed/factorial designs
        experimental_factors = [k for k, v in factors.items() if v.get("type") == "experimental"]

        if len(experimental_factors) >= 2:
            f1, f2 = experimental_factors[0], experimental_factors[1]
            content += f"**Factorial Analysis:** This crossed design allows testing main effects of {f1} and {f2}, as well as their interaction. Use a full factorial model (e.g., `~ {f1} * {f2}`) to capture all experimental effects.\n\n"

        if classification_rels:
            classifier = classification_rels[0].get("classifier", "")
            content += f"**Cell-Level Analysis:** For cell-type-specific analyses, model the factorial structure while accounting for {classifier} labels. Consider using mixed-effects models with {classifier}-specific random effects if cell counts vary substantially.\n\n"

        content += "**Multiple Testing:** With multiple factors and their interactions, carefully control for multiple testing using appropriate correction methods (e.g., FDR, Bonferroni)."

    else:
        # Simple/other designs
        content += "**Statistical Modeling:** Consider the hierarchical structure of your data when choosing statistical models. Account for within-sample correlation using appropriate methods (mixed-effects models, GEE, etc.).\n\n"

        if classification_rels:
            classifier = classification_rels[0].get("classifier", "")
            content += f"**Classification Analysis:** The `{classifier}` labels provide a natural stratification for subgroup analyses. Consider both cell-type-specific and cell-type-aggregated analyses.\n\n"

        content += "**Replication:** Ensure that biological replicates are properly identified and accounted for in the analysis to enable valid statistical inference."

    return content


def generate_experiment_card(data: Dict[str, Any]) -> str:
    """Generate the experiment card markdown content."""

    # Extract data
    h5ad_file = data.get("h5ad_file", "unknown.h5ad")
    total_cells = data.get("total_cells", 0)
    design_type = data.get("design_type", "unknown")
    species = data.get("species", "unknown")
    edviz_grammar = data.get("edviz_grammar", "")
    edviz_diagram = data.get("edviz_diagram", "")
    experimental_context = data.get("experimental_context", {})
    factors = data.get("factors", {})
    relationships = data.get("relationships", [])
    design_notes = data.get("design_notes", [])
    tool_version = data.get("tool_version", "0.1.0")

    analysis_date = datetime.now().strftime("%Y-%m-%d")

    # Build YAML frontmatter
    yaml_factors = list(factors.keys())
    frontmatter = f"""---
analysis_date: "{analysis_date}"
h5ad_file: "{h5ad_file}"
species: "{species}"
total_cells: {total_cells}
design_type: "{design_type}"
edviz_grammar: "{edviz_grammar}"
factors:
{chr(10).join(f"  - {f}" for f in yaml_factors)}
tool_version: "{tool_version}"
---
"""

    # Build Dataset Information section
    # Map species to common names
    species_names = {
        "human": "Human (Homo sapiens)",
        "mouse": "Mouse (Mus musculus)",
        "zebrafish": "Zebrafish (Danio rerio)",
        "drosophila": "Fruit fly (Drosophila melanogaster)",
        "unknown": "Unknown"
    }
    species_display = species_names.get(species, species.title())

    dataset_section = f"""# Experimental Design Card

## Dataset Information

**File:** {h5ad_file}
**Analysis Date:** {analysis_date}
**Species:** {species_display}
**Total Cells:** {format_number(total_cells)}
"""

    # Build Experimental Context section (if available)
    context_section = ""
    if experimental_context:
        experiment_type = experimental_context.get("experiment_type", "")
        research_question = experimental_context.get("research_question", "")
        factor_descriptions = experimental_context.get("factor_descriptions", {})

        if experiment_type or research_question or factor_descriptions:
            context_section = "\n## Experimental Context\n\n"

            if experiment_type:
                context_section += f"**Experiment Type:** {experiment_type}\n\n"

            if research_question:
                context_section += f"**Research Question:** {research_question}\n\n"

            if factor_descriptions:
                context_section += "**Factor Descriptions:**\n\n"
                for factor, description in factor_descriptions.items():
                    context_section += f"- **{to_title_case(factor)}**: {description}\n"
                context_section += "\n"

    # Build Identified Factors table
    factors_table = "\n### Identified Factors\n\n"
    factors_table += "| Factor | Levels | Type |\n"
    factors_table += "|--------|--------|------|\n"

    for fname, fdata in factors.items():
        n_levels = len(fdata.get("categories", []))
        ftype = get_factor_display_type(fdata.get("type", ""))
        display_name = to_title_case(fname)
        factors_table += f"| {display_name} | {n_levels} | {ftype} |\n"

    # Build Design Classification section
    classification_text = "\n### Design Classification\n\n"

    # Determine design description based on type and relationships
    nested_rels = [r for r in relationships if r.get("type") == "nested"]
    classification_rels = [r for r in relationships if r.get("type") == "classification"]

    if nested_rels and len(nested_rels) > 0:
        parent = nested_rels[0].get("parent", "")
        child = nested_rels[0].get("child", "")

        if len(nested_rels) == 1:
            classification_text += f"This dataset exhibits a **nested design**. The factor `{child}` is nested within `{parent}`, meaning each {to_title_case(child).lower()} belongs to exactly one {parent} condition."
        else:
            classification_text += f"This dataset exhibits a **hierarchical nested design** with multiple levels of nesting."

        if classification_rels:
            classifier = classification_rels[0].get("classifier", "")
            classification_text += f" {to_title_case(classifier)}s are observed across all {child}s, creating a crossed relationship with the nested structure."
    else:
        # Crossed or simple design
        experimental_factors = [k for k, v in factors.items() if v.get("type") == "experimental"]
        if len(experimental_factors) >= 2:
            classification_text += f"This dataset exhibits a **factorial crossed design** where {' and '.join(f'`{f}`' for f in experimental_factors)} are fully crossed, meaning all combinations of factor levels are present."
        else:
            classification_text += f"This dataset represents a simple experimental design."

    classification_text += "\n"

    # Build Design Diagram section
    diagram_section = "\n### Design Diagram\n\n```\n"
    diagram_section += edviz_diagram if edviz_diagram else "(Diagram not available)"
    diagram_section += "\n```\n"

    # Build Grammar Notation section
    grammar_section = "\n### Grammar Notation\n\n```\n"
    grammar_section += edviz_grammar if edviz_grammar else "(Grammar not available)"
    grammar_section += "\n```\n"

    # Build Cell Distribution section
    distribution_section = "\n## Cell Distribution\n\n"

    for fname, fdata in factors.items():
        counts = fdata.get("counts", [])
        if counts:
            stats = calculate_summary_stats(counts)
            range_str = format_range(stats)
            distribution_section += f"**Cells per {fname}:** {range_str}  \n"

    # Build Analysis Considerations section
    analysis_section = "\n## Analysis Considerations\n\n"
    analysis_section += generate_analysis_section(design_type, factors, relationships)

    # Build Design Notes section (optional)
    notes_section = ""
    if design_notes:
        notes_section = "\n\n## Design Notes\n\n"
        for note in design_notes:
            notes_section += f"{note}\n\n"
        notes_section = notes_section.rstrip() + "\n"

    # Combine all sections
    card = frontmatter
    card += dataset_section
    if context_section:
        card += context_section
    card += "\n## Design Structure\n"
    card += factors_table
    card += classification_text
    card += diagram_section
    card += grammar_section
    card += distribution_section
    card += analysis_section
    if notes_section:
        card += notes_section

    return card


def main():
    """Main function."""
    if len(sys.argv) < 3:
        print("Usage: generate_experiment_card.py <input.json> <output.md>", file=sys.stderr)
        print("       or: ... | generate_experiment_card.py - <output.md>", file=sys.stderr)
        return 1

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Read input
    try:
        if input_file == "-":
            data = json.load(sys.stdin)
        else:
            with open(input_file, 'r') as f:
                data = json.load(f)
    except Exception as e:
        print(f"Error reading input: {e}", file=sys.stderr)
        return 1

    # Generate card
    try:
        card_content = generate_experiment_card(data)
    except Exception as e:
        print(f"Error generating experiment card: {e}", file=sys.stderr)
        return 1

    # Write output
    try:
        with open(output_file, 'w') as f:
            f.write(card_content)
        print(f"Experiment card written to: {output_file}")
        return 0
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
