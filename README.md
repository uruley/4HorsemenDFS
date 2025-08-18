# 4 Horsemen DFS Optimizer

A comprehensive Daily Fantasy Sports (DFS) optimization platform for building optimal lineups across multiple sports and platforms.

## Project Structure

```
4HorsemenDFS/
├── scripts/           # Core processing scripts
├── utils/            # Utility functions and helpers
├── features/         # Feature engineering pipeline
├── models/           # ML model registry and management
├── config/           # Configuration files and mappings
├── tests/            # Test files and sample data
├── frontend/         # React frontend application
├── server.py         # Flask backend server
└── requirements.txt  # Python dependencies
```

## Features (TODO)

- **Data Normalization**: Standardize player and team names across data sources
- **Projection Engine**: Generate player performance projections
- **Feature Engineering**: Build predictive features from raw data
- **Lineup Optimization**: Create optimal DFS lineups within salary constraints
- **Multi-Platform Support**: DraftKings, FanDuel, and other DFS platforms
- **Web Interface**: User-friendly frontend for lineup management

## Setup Instructions

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Run the Flask server:
```bash
python server.py
```

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm start
```

## Configuration

- **team_alias.csv**: Team name mappings across data sources
- **name_map.csv**: Player name normalization mappings
- **features_contract.yml**: Feature specifications and data contracts

## Development Status

This project is currently in the initial setup phase. All files contain placeholder code with TODO comments indicating where actual implementation logic should be added.

## Next Steps

1. Implement data normalization functions in `utils/normalize.py`
2. Build feature engineering pipeline in `features/build.py`
3. Develop projection algorithms in `scripts/projection_engine.py`
4. Create lineup optimization logic in `server.py`
5. Build out the React frontend components
6. Add comprehensive testing

## Contributing

This is a placeholder structure. All files contain TODO comments indicating where actual implementation should occur.

## License

MIT License
