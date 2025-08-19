# 4HorsemenDFS Optimizer V2

Enhanced DraftKings NFL lineup optimizer with advanced name matching and configurable constraints.

## Quick Start

### Basic Usage
```bash
# Single optimal lineup
python scripts/optimize_lineups_v2.py --projections projections.csv --salaries data/DKSalaries.csv

# Multiple lineups with constraints
python scripts/optimize_lineups_v2.py --projections projections.csv --salaries data/DKSalaries.csv \
    --num-lineups 20 --min-salary 49500 --qb-stack 1 --max-team 4
```

### Input Formats

**Option 1: Clean projections file**
- Columns: `name`, `pos`, `proj_points`, `team`, `opp`
- Example: `projections.csv`

**Option 2: DraftKings export**
- Columns: `Position`, `Name`, `TeamAbbrev`, `AvgPointsPerGame`, etc.
- Automatically converted to required schema

## CLI Options

### Required
- `--projections`: Projections CSV file (clean or DK export)
- `--salaries`: DraftKings salaries CSV file

### Optional
- `--aliases`: Name aliases CSV (default: `data/name_aliases.csv`)
- `--output`: Output file for single lineup (default: `optimal_lineup.csv`)
- `--salary-cap`: Salary cap (default: 50000)
- `--min-salary`: Minimum total salary (default: 0)

### Multiple Lineups
- `--num-lineups`: Number of lineups to generate (default: 1)
- `--uniq-shared`: Max shared slots with prior lineups (default: 7)
- `--alpha`: Randomness factor (default: 0.04)

### Constraints
- `--qb-stack`: QB stack requirement 0/1/2 (default: 1)
- `--max-team`: Max players per team (default: 4)
- `--no-rb-vs-dst`: Prohibit RB vs opposing DST

### Exposure
- `--max-exposure`: Max player exposure (default: 0.35)
- `--max-qb-exposure`: Max QB exposure (default: 0.4)
- `--max-dst-exposure`: Max DST exposure (default: 0.4)

## Examples

### Tournament Lineups
```bash
python scripts/optimize_lineups_v2.py \
    --projections projections.csv \
    --salaries data/DKSalaries.csv \
    --num-lineups 150 \
    --min-salary 49500 \
    --uniq-shared 6 \
    --alpha 0.06 \
    --qb-stack 2 \
    --max-team 3 \
    --max-exposure 0.25
```

### Cash Game
```bash
python scripts/optimize_lineups_v2.py \
    --projections projections.csv \
    --salaries data/DKSalaries.csv \
    --num-lineups 1 \
    --min-salary 49000 \
    --qb-stack 1 \
    --max-team 4 \
    --no-rb-vs-dst
```

### DK Export Direct
```bash
python scripts/optimize_lineups_v2.py \
    --projections data/DKSalaries.csv \
    --salaries data/DKSalaries.csv \
    --num-lineups 10 \
    --min-salary 49500
```

## Outputs

- **Single lineup**: `optimal_lineup.csv`
- **Multiple lineups**: `outputs/lineup_XX.csv`
- **Reports**: 
  - `reports/player_exposure.csv`
  - `reports/team_exposure.csv`
  - `reports/stacks.csv`
  - `reports/unmatched_players.csv`
  - `reports/ambiguous_matches.csv`

## Testing

Run the test suite:
```bash
python test_optimizer.py
```

Tests both clean projections and DK export formats, plus multiple lineup generation.

## Features

- ✅ **Windows-safe**: No Unicode/emoji crashes
- ✅ **Flexible input**: Accepts both clean and DK export formats
- ✅ **Advanced matching**: Team-aware name disambiguation
- ✅ **Configurable constraints**: QB stacking, team limits, RB vs DST
- ✅ **Multi-lineup generation**: With uniqueness and exposure controls
- ✅ **Banded randomness**: Salary-based projection variance
- ✅ **Comprehensive reporting**: Player/team exposure, stacking analysis
