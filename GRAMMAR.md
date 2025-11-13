# edviz Grammar Specification

**Version**: 1.0
**Status**: Production
**Purpose**: Formal specification for AI agents and implementers

## Overview

The edviz grammar is a domain-specific language (DSL) for expressing experimental designs with hierarchical nesting, factorial crossing, classification, confounding, and batch effects.

## Formal Grammar (EBNF)

```ebnf
(* Top-level design *)
design ::= statement_list

statement_list ::= statement+

statement ::= confound_statement | comment | EOL

confound_statement ::= confound_expr | batch_expr

(* Precedence levels from lowest to highest *)
confound_expr ::= batch_expr ( CONFOUND batch_expr )*

batch_expr ::= crossing_expr ( BATCH crossing_expr )*

crossing_expr ::= nesting_expr ( ( CROSS | PARTIAL_CROSS ) nesting_expr )*

nesting_expr ::= classification_expr ( NEST classification_expr )*

classification_expr ::= primary_expr ( CLASSIFY primary_expr )?

primary_expr ::= factor | confound_group | paren_expr

confound_group ::= LBRACE factor+ RBRACE

paren_expr ::= LPAREN confound_expr RPAREN

factor ::= IDENTIFIER size_spec

size_spec ::= balanced | unbalanced | approximate

balanced ::= LPAREN NUMBER RPAREN

unbalanced ::= LBRACKET NUMBER ( PIPE NUMBER )* RBRACKET

approximate ::= LPAREN TILDE NUMBER RPAREN

comment ::= HASH .*? EOL
```

## Tokens

### Token Definitions

| Token | Pattern | Example | Description |
|-------|---------|---------|-------------|
| `IDENTIFIER` | `[A-Za-z_][A-Za-z0-9_]*` | `Patient`, `Sample_A` | Factor name |
| `NUMBER` | `[0-9]+` or `[0-9]+k` | `42`, `5k` | Count (k = ×1000) |
| `NEST` | `>` | `>` | Nesting operator |
| `CROSS` | `×` or `*` | `×` | Full crossing |
| `PARTIAL_CROSS` | `◊` or `<>` | `◊` | Partial crossing |
| `CLASSIFY` | `:` | `:` | Classification |
| `BATCH` | `==` | `==` | Batch effect |
| `CONFOUND` | `≈≈` or `~~` | `≈≈` | Confounding |
| `LPAREN` | `(` | `(` | Left parenthesis |
| `RPAREN` | `)` | `)` | Right parenthesis |
| `LBRACKET` | `[` | `[` | Left bracket |
| `RBRACKET` | `]` | `]` | Right bracket |
| `LBRACE` | `{` | `{` | Left brace |
| `RBRACE` | `}` | `}` | Right brace |
| `PIPE` | `\|` | `\|` | Pipe (separator) |
| `TILDE` | `~` | `~` | Approximate marker |
| `HASH` | `#` | `#` | Comment start |
| `WHITESPACE` | `[ \t]+` | ` ` | Ignored |
| `EOL` | `\n` or `\r\n` | `\n` | Line terminator |

### Token Precedence

Operators in order of precedence (highest to lowest):

1. `()` - Parentheses (grouping)
2. `:` - Classification (terminal operation)
3. `>` - Nesting (hierarchical)
4. `×`, `◊` - Crossing (factorial), left-associative
5. `==` - Batch effects (metadata)
6. `≈≈` - Confounding (metadata), left-associative

### Special Token Notes

- **k suffix**: `5k` is lexed as NUMBER with value 5000
- **Unicode alternatives**: `×` can be `*`, `◊` can be `<>`, `≈≈` can be `~~`
- **Whitespace**: Required between identifiers and numbers, optional elsewhere
- **Comments**: From `#` to end of line, completely ignored

## Factor Specifications

### Balanced Factors
```
Factor(n)
```
- **Semantics**: Factor with exactly `n` levels, evenly distributed
- **Example**: `Treatment(3)` = 3 treatment groups
- **Constraint**: `n` must be positive integer

### Unbalanced Factors
```
Factor[n1|n2|...|nk]
```
- **Semantics**: Factor with varying counts across branches
- **Example**: `Clinic[45|38|52]` = 3 clinics with different patient counts
- **Constraint**: All `ni` must be positive integers
- **Usage**: Represents real-world imbalance

### Approximate Factors
```
Factor(~n)
```
- **Semantics**: Factor with approximately `n` items (exact count unknown)
- **Example**: `Cell(~5000)` = approximately 5000 cells
- **Constraint**: Used for estimates (e.g., flow cytometry cell counts)
- **Display**: Shown as `~n` in output

### k Suffix
```
Factor(5k) ≡ Factor(5000)
```
- **Semantics**: Shorthand for thousands
- **Example**: `Cell(8k)` = `Cell(8000)`
- **Parsing**: Lexer converts `8k` → `8000`

## Operators

### Nesting (`>`)

**Syntax**: `A > B`

**Semantics**:
- Factor A contains/nests factor B
- Each instance of A has multiple instances of B
- Hierarchical relationship
- B instances are unique to their parent A instance

**Example**:
```
Hospital(4) > Patient(20)
```
- 4 hospitals, each with 20 patients
- Total: 80 patients (4 × 20)
- Each patient belongs to exactly one hospital

**Graph**: Creates directed edge A → B in nesting DAG

**Observation Count**: Multiplicative

### Full Crossing (`×`)

**Syntax**: `A × B`

**Semantics**:
- All combinations of A and B occur
- Factorial design
- Each level of A paired with each level of B

**Example**:
```
Treatment(3) × Timepoint(4)
```
- 3 treatments, 4 timepoints
- 12 combinations total (3 × 4)
- Every treatment measured at every timepoint

**Graph**: Creates edges between A and B (bidirectional or special crossing edge)

**Observation Count**: Multiplicative

### Partial Crossing (`◊`)

**Syntax**: `A ◊ B`

**Semantics**:
- Some but not all combinations of A and B occur
- Incomplete factorial design
- Used for resource-constrained designs

**Example**:
```
Sample(10) ◊ Treatment(5)
```
- Not all samples receive all treatments
- Exact count depends on design
- Indicates incompleteness

**Graph**: Creates partial crossing edge

**Observation Count**: Cannot be calculated precisely (marked approximate)

### Classification (`:`)

**Syntax**: `A : B`

**Semantics**:
- Instances of A are classified/categorized into B types
- B is a property/label of A, not a separate factor
- **Terminal operation**: No operations allowed after classification

**Example**:
```
Cell(5000) : CellType(35)
```
- 5000 cells classified into 35 cell types
- CellType is not a separate nesting level
- Total observations: 5000 (cells), not 5000×35

**Graph**: Creates classification edge (A classifies B)

**Observation Count**: Does NOT multiply

**Constraint**: Must be last operation in expression chain

### Confounding (`≈≈`)

**Syntax**: `{A ≈≈ B}` or `A ≈≈ B`

**Semantics**:
- Factors A and B are perfectly confounded
- Cannot distinguish their effects
- They vary together completely

**Example**:
```
{Center(3) ≈≈ Protocol(2)}
```
- Center and Protocol are confounded
- Each center uses exactly one protocol
- Cannot separate center effects from protocol effects

**Typical Usage**: Enclosed in braces `{...}` when part of larger design

**Graph**: Creates confounding edge (metadata, not structural)

**Observation Count**: Factors count once (they're the same variation)

**Metadata**: Stored in `confound_groups` metadata field

### Batch Effects (`==`)

**Syntax**: `BatchFactor(n) == TargetFactor`

**Status**: ⚠️ **NOT IMPLEMENTED IN PARSER**

**Semantics**:
- BatchFactor affects measurements of TargetFactor
- Metadata relationship, not structural
- Indicates technical variation source

**Workaround**: Use programmatic API
```python
design.add_factor("ProcessingBatch", 4, "batch")
design.add_batch_effect("ProcessingBatch", ["Sample"])
```

**Why Not Implemented**: Requires factor references (no size spec), parser doesn't support this

**Recommendation**: Document as programmatic-only feature

## Grouping

### Confound Groups (`{...}`)

**Syntax**: `{Factor1 Factor2 ... FactorN}`

**Semantics**:
- Group factors that are confounded with each other
- Typically used with `≈≈` operator

**Example**:
```
{Center(3) ≈≈ Protocol(2)} > Patient(30)
```

**Parsing**: Creates confound relationships between all factors in group

**Visual**: Factors displayed side-by-side with `≈≈≈≈` connection

### Parentheses (`(...)`)

**Syntax**: `(expression)`

**Semantics**:
- Override default precedence
- Group sub-expressions

**Example**:
```
(Treatment(2) × Timepoint(4)) > Sample(3)
```

**Parsing**: Inner expression evaluated first

**Note**: Rarely needed due to clear precedence rules

## Parsing Algorithm

### Recursive Descent Parser

The parser uses **recursive descent** with **precedence climbing**:

```
parse_design()
  ↓
parse_confounding()
  ↓
parse_batch()
  ↓
parse_crossing()
  ↓
parse_nesting()
  ↓
parse_classification()
  ↓
parse_primary()
  ↓
parse_factor()
```

### Precedence Levels

| Level | Operator | Associativity | Function |
|-------|----------|---------------|----------|
| 0 | `()` | N/A | `parse_primary()` |
| 1 | `:` | Right | `parse_classification()` |
| 2 | `>` | Left | `parse_nesting()` |
| 3 | `×`, `◊` | Left | `parse_crossing()` |
| 4 | `==` | Left | `parse_batch()` |
| 5 | `≈≈` | Left | `parse_confounding()` |

### Key Parsing Rules

1. **Factor Definition**: Every factor must have size specification on first mention
2. **No Forward References**: Factors must be defined before referenced (currently not enforced)
3. **Classification Terminal**: `:` cannot be followed by other operators
4. **Confound Groups**: `{...}` creates pairwise confounding between all members
5. **Comments**: Stripped before parsing
6. **Whitespace**: Normalized, only significant between tokens

## Complete Examples

### Example 1: Simple Hierarchy
```
Site(3) > Patient(20) > Sample(2) > Cell(5000)
```

**Parse tree**:
```
nesting(
  nesting(
    nesting(
      Site(3),
      Patient(20)
    ),
    Sample(2)
  ),
  Cell(5000)
)
```

**Relationships**:
- Site nests Patient
- Patient nests Sample
- Sample nests Cell

**Observations**: 3 × 20 × 2 × 5000 = 600,000

---

### Example 2: With Classification
```
Sample(100) > Cell(5000) : CellType(35)
```

**Parse tree**:
```
nesting(
  Sample(100),
  classification(
    Cell(5000),
    CellType(35)
  )
)
```

**Relationships**:
- Sample nests Cell
- Cell classifies CellType

**Observations**: 100 × 5000 = 500,000 cells (NOT ×35)

---

### Example 3: Crossed Factorial
```
Treatment(3) × Dose(4) × Timepoint(6)
```

**Parse tree**:
```
crossing(
  crossing(
    Treatment(3),
    Dose(4)
  ),
  Timepoint(6)
)
```

**Relationships**:
- Treatment crosses Dose
- (Treatment, Dose) crosses Timepoint

**Observations**: 3 × 4 × 6 = 72 combinations

---

### Example 4: Mixed Design
```
Hospital(4) > Patient(15) × Treatment(2) > Sample(3)
```

**Parse tree**:
```
nesting(
  nesting(
    Hospital(4),
    crossing(
      Patient(15),
      Treatment(2)
    )
  ),
  Sample(3)
)
```

**Known Issue**: Parser creates `Patient crosses Sample` AND `Treatment nests Sample`
- See KNOWN_ISSUES.md for details

---

### Example 5: Confounded Factors
```
{Center(3) ≈≈ Protocol(2)} > Patient(30) > Sample(2)
```

**Parse tree**:
```
nesting(
  nesting(
    confound_group(
      Center(3),
      Protocol(2)
    ),
    Patient(30)
  ),
  Sample(2)
)
```

**Relationships**:
- Center confounded with Protocol
- Center nests Patient
- Protocol nests Patient (both, since confounded)
- Patient nests Sample

**Metadata**: `confound_groups = [['Center', 'Protocol']]`

---

### Example 6: Unbalanced Design
```
Clinic[45|38|52|29] > Patient(10) > Visit(3)
```

**Parse tree**:
```
nesting(
  nesting(
    Clinic([45,38,52,29]),
    Patient(10)
  ),
  Visit(3)
)
```

**Observations**: (45+38+52+29) × 10 × 3 = 4920

---

### Example 7: Approximate Counts
```
Sample(100) > Cell(~8000) : CellType(42)
```

**Parse tree**:
```
nesting(
  Sample(100),
  classification(
    Cell(~8000),
    CellType(42)
  )
)
```

**Observations**: ~800,000 (approximate)

---

### Example 8: Complex Real-World Design
```
{Center(3) ≈≈ Protocol(2)} > Patient[30|25|18] > Sample(2) ◊ Treatment(3) × Timepoint(4) > Cell(~5000) : CellType(42)
```

**Features**:
- Confounding: Center ≈≈ Protocol
- Unbalanced: Patient counts vary by center
- Partial crossing: Not all samples get all treatments
- Full crossing: Treatments fully crossed with timepoints
- Nesting: Multiple levels
- Classification: Cells classified into types
- Approximate: ~5000 cells per sample

**Observations**: ~511,584 (approximate due to ◊ and ~)

## Implementation Notes

### Current Implementation (Python)

**File**: `edviz/parser.py`

**Key Classes**:
- `Token`: Represents a lexical token
- `DesignGrammarParser`: Main parser class

**Key Methods**:
- `tokenize()`: Lexical analysis
- `parse()`: Syntax analysis
- `_parse_confounding()` through `_parse_factor()`: Recursive descent

**Deviations from Spec**:
1. Batch effects (`==`) not implemented in grammar (see KNOWN_ISSUES.md)
2. Mixed crossing/nesting creates unexpected relationships (see KNOWN_ISSUES.md)

### Testing

**File**: `edviz/tests/test_parser.py`

**Coverage**:
- All token types
- All operators
- Precedence rules
- Edge cases
- Error conditions

**Test Count**: 30+ parser tests

## Validation Rules

### Structural Validation

1. **No Cycles**: Nesting relationships must form a DAG
2. **Classification Terminal**: No operations after `:`
3. **Positive Counts**: All factor sizes must be > 0
4. **Unbalanced Non-Empty**: `[n1|n2|...]` must have at least one value
5. **Approximate Format**: `~n` where n is valid number

### Semantic Validation

1. **Factor Uniqueness**: Factor names should be unique (case-sensitive)
2. **Relationship Validity**: Source and target factors must exist
3. **No Self-Loops**: Factor cannot relate to itself

**File**: `edviz/validators.py`

## Error Handling

### Lexical Errors

- Invalid characters → `ValueError: Unexpected character`
- Unclosed brackets → `ValueError: Unmatched brackets`

### Syntax Errors

- Missing size spec → `ValueError: Expected size specification`
- Missing closing paren → `ValueError: Expected ')' at position N`
- Invalid number → `ValueError: Invalid number format`

### Semantic Errors

- Undefined factor → `ValueError: Unknown factor in relationship`
- Cycle detected → `ValidationError: Cycle detected in nesting`
- Classification not terminal → `ValidationError: Classification must be terminal`

## Output Data Structures

### ParsedDesign

```python
@dataclass
class ParsedDesign:
    factors: List[Factor]          # All factors
    relationships: List[Relationship]  # All relationships
    metadata: Dict[str, Any]       # Confound groups, etc.
```

### Factor

```python
@dataclass
class Factor:
    name: str
    n: Union[int, List[int], str]  # size specification
    type: FactorType  # "factor" | "batch"
```

### Relationship

```python
@dataclass
class Relationship:
    from_factor: str
    to_factor: str
    rel_type: RelationshipType  # "nests" | "crosses" | ...
```

## Extensions and Future Work

### Potential Grammar Extensions

1. **Factor References**: `@FactorName` for references without size
2. **Ranges**: `Factor(10-20)` for variable counts
3. **Ratios**: `Factor(2:1)` for ratio specifications
4. **Conditions**: `[if condition]` for conditional relationships
5. **Inline Batch**: `BatchFactor(4) == { ... }` for batch scope

### Backward Compatibility

Any grammar extensions must:
- Not break existing valid grammar strings
- Be opt-in (require new syntax)
- Be clearly documented

## Reference Implementation

**Language**: Python 3.8+
**Dependencies**: None (for parser)
**Files**:
- `edviz/parser.py` - Parser implementation
- `edviz/tests/test_parser.py` - Test suite
- `KNOWN_ISSUES.md` - Known limitations

## Changelog

**v1.0** (2024-11-10):
- Initial formal specification
- Documents current implementation
- Notes known limitations

---

## Quick Reference Card

### Operators
| Operator | Name | Example | Observations |
|----------|------|---------|--------------|
| `>` | Nest | `A(2) > B(3)` | 2 × 3 = 6 |
| `×` | Cross | `A(2) × B(3)` | 2 × 3 = 6 |
| `◊` | Partial | `A(2) ◊ B(3)` | < 6 |
| `:` | Classify | `A(6) : B(3)` | 6 (not ×3) |
| `≈≈` | Confound | `{A ≈≈ B}` | Metadata |
| `==` | Batch | `A == B` | Not in grammar |

### Factor Sizes
| Syntax | Meaning | Count |
|--------|---------|-------|
| `F(n)` | Balanced | n |
| `F[a\|b\|c]` | Unbalanced | a+b+c |
| `F(~n)` | Approximate | ~n |
| `F(5k)` | Thousands | 5000 |

### Precedence
```
()  highest
:
>
× ◊
==
≈≈  lowest
```
