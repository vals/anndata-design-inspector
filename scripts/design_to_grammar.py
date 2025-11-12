#!/usr/bin/env python3
"""
Convert experimental design structure to edviz grammar format.

Takes JSON input describing factors, their relationships, and cell counts,
and outputs a valid edviz grammar string.

Usage:
    python scripts/design_to_grammar.py <design.json>
    echo '{"factors": {...}, "relationships": [...]}' | python scripts/design_to_grammar.py -

Input JSON format:
{
  "factors": {
    "factor_name": {
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
  ]
}

Output:
    Valid edviz grammar string (e.g., "Genotype(2) > Sample(4) : CellType(6)")
"""

import json
import sys
from typing import Dict, List, Any, Optional, Tuple


def format_count(count: int, approximate: bool = False) -> str:
    """
    Format count for edviz grammar.

    Args:
        count: The count value
        approximate: If True, use ~ prefix and k/m suffix for large numbers

    Returns:
        Formatted count string (e.g., "4", "~21k", "~1.2m")
    """
    if approximate and count >= 1000:
        if count >= 1_000_000:
            return f"~{count / 1_000_000:.1f}m".rstrip('0').rstrip('.')
        else:
            return f"~{count / 1000:.1f}k".rstrip('0').rstrip('.')
    return str(count)


def is_balanced(counts: List[int], tolerance: float = 0.1) -> bool:
    """
    Check if counts are balanced (approximately equal).

    Args:
        counts: List of counts
        tolerance: Relative tolerance for considering counts balanced

    Returns:
        True if counts are balanced within tolerance
    """
    if not counts or len(counts) == 1:
        return True

    avg = sum(counts) / len(counts)
    if avg == 0:
        return True

    return all(abs(c - avg) / avg <= tolerance for c in counts)


def to_camel_case(name: str) -> str:
    """
    Convert a name to CamelCase for edviz grammar compatibility.

    Args:
        name: Factor name (may contain underscores or spaces)

    Returns:
        CamelCase version of the name
    """
    # Replace underscores with spaces, then title case each word
    words = name.replace('_', ' ').split()
    return ''.join(word.capitalize() for word in words)


def format_factor_counts(factor_name: str, categories: List[str], counts: List[int],
                         approximate: bool = False) -> str:
    """
    Format a factor with its counts in edviz grammar.

    Args:
        factor_name: Name of the factor
        categories: List of category names
        counts: List of counts for each category
        approximate: Whether to use approximate notation

    Returns:
        Formatted factor string (e.g., "Genotype(2)", "Sample[5354|5354|5354|5355]")
    """
    n_categories = len(categories)
    # Convert to CamelCase for edviz compatibility (no spaces allowed)
    factor_name = to_camel_case(factor_name)

    if is_balanced(counts):
        # Use balanced notation: Factor(n)
        count_str = format_count(n_categories, approximate=False)
        return f"{factor_name}({count_str})"
    else:
        # Use unbalanced notation: Factor[n1|n2|n3]
        count_strs = [format_count(c, approximate=approximate) for c in counts]
        return f"{factor_name}[{'|'.join(count_strs)}]"


def find_root_factors(factors: Dict[str, Any], relationships: List[Dict[str, str]]) -> List[str]:
    """
    Find factors that have no parent (root of hierarchy).

    Args:
        factors: Dictionary of factors
        relationships: List of relationships

    Returns:
        List of root factor names
    """
    all_factors = set(factors.keys())
    child_factors = set()
    classifier_factors = set()

    for rel in relationships:
        if rel.get("type") == "nested":
            child_factors.add(rel["child"])
        elif rel.get("type") == "crossed":
            # Both factors in crossing might have parents
            pass
        elif rel.get("type") == "classification":
            # Classifiers are not root factors - they annotate other factors
            classifier_factors.add(rel.get("classifier"))

    # Root factors are those that are neither children nor classifiers
    roots = all_factors - child_factors - classifier_factors
    return list(roots)


def get_children(factor: str, relationships: List[Dict[str, str]],
                rel_type: str = "nested") -> List[str]:
    """Get child factors for a given parent factor."""
    children = []
    for rel in relationships:
        if rel.get("type") == rel_type and rel.get("parent") == factor:
            children.append(rel["child"])
    return children


def get_classifier(factor: str, relationships: List[Dict[str, str]]) -> Optional[str]:
    """Get classifier factor for a given factor."""
    for rel in relationships:
        if rel.get("type") == "classification" and rel.get("factor") == factor:
            return rel.get("classifier")
    return None


def build_grammar_recursive(factor: str, factors: Dict[str, Any],
                            relationships: List[Dict[str, str]],
                            use_approximate: bool = False) -> str:
    """
    Recursively build grammar string for a factor and its descendants.

    Args:
        factor: Current factor name
        factors: Dictionary of all factors
        relationships: List of relationships
        use_approximate: Whether to use approximate counts for large numbers

    Returns:
        Grammar string for this factor subtree
    """
    factor_data = factors[factor]
    categories = factor_data["categories"]
    counts = factor_data["counts"]

    # Format this factor
    # Use approximate notation only for classifications (cell counts)
    is_classification = factor_data.get("type") == "classification"
    grammar = format_factor_counts(
        factor,  # Will be converted to CamelCase in format_factor_counts
        categories,
        counts,
        approximate=use_approximate and is_classification
    )

    # Find nested children
    children = get_children(factor, relationships, "nested")

    if children:
        # Add nesting operator and process children
        child_grammars = [
            build_grammar_recursive(child, factors, relationships, use_approximate)
            for child in children
        ]
        grammar += " > " + " > ".join(child_grammars)

    # Check for classifier (classification relationship)
    classifier = get_classifier(factor, relationships)
    if classifier and classifier in factors:
        classifier_data = factors[classifier]
        # For classifiers, just show the number of categories, not the distribution
        # Classification is about labeling, not about the count distribution
        n_categories = len(classifier_data["categories"])
        classifier_name = to_camel_case(classifier)
        classifier_grammar = f"{classifier_name}({n_categories})"
        grammar += " : " + classifier_grammar

    return grammar


def convert_design_to_grammar(design: Dict[str, Any]) -> str:
    """
    Convert design structure to edviz grammar string.

    Args:
        design: Dictionary containing 'factors' and 'relationships'

    Returns:
        Valid edviz grammar string
    """
    factors = design["factors"]
    relationships = design["relationships"]

    # Find root factors
    roots = find_root_factors(factors, relationships)

    if not roots:
        raise ValueError("No root factors found - possible circular dependency")

    # Build grammar for each root
    root_grammars = []
    for root in roots:
        root_grammar = build_grammar_recursive(root, factors, relationships)
        root_grammars.append(root_grammar)

    # If multiple roots, they should be crossed
    if len(root_grammars) == 1:
        return root_grammars[0]
    else:
        # Multiple independent factors should be crossed
        return " × ".join(root_grammars)


def main():
    """Main function."""
    # Read input
    if len(sys.argv) > 1 and sys.argv[1] != "-":
        with open(sys.argv[1], 'r') as f:
            design = json.load(f)
    else:
        design = json.load(sys.stdin)

    # Convert to grammar
    try:
        grammar = convert_design_to_grammar(design)
        print(grammar)
        return 0
    except Exception as e:
        print(f"Error converting design to grammar: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
