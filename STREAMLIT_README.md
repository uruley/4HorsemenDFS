# 🚀 Streamlit App for 4HorsemenDFS

## Quick Start

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the app:**
   ```bash
   streamlit run app.py
   ```

3. **Open your browser** to the URL shown (usually http://localhost:8501)

## What It Does

- **Data Tab**: Upload and preview your projections and DraftKings salary CSVs
- **Matching Tab**: View name matching results and download reports
- **Optimize Tab**: Run the optimizer with your settings and see console output
- **Lineups Tab**: Browse and download generated lineups
- **Reports Tab**: View exposure and stacking analysis

## File Structure Expected

The app expects these files to exist:
- `scripts/optimize_lineups_v2.py` - Your optimizer script
- `outputs/` - Directory for generated lineups
- `reports/` - Directory for analysis reports

## Usage

1. Upload your **Projections CSV** (required)
2. Upload your **DraftKings Salaries CSV** (required)  
3. Optionally upload **Name Aliases CSV** for better matching
4. Adjust settings in the sidebar:
   - Salary cap (default: $50,000)
   - Minimum spend
   - Number of lineups
   - Randomness factor
   - Max exposure per player
5. Click "⚡ Optimize" to run
6. View results in the tabs

## Troubleshooting

- **"Module not found"**: Make sure you're in the repo root directory
- **"Script not found"**: Verify `scripts/optimize_lineups_v2.py` exists
- **Permission errors**: Check that the `outputs/` and `reports/` directories are writable

## Moving to Production

This Streamlit app is perfect for:
- ✅ Local development and testing
- ✅ Team collaboration
- ✅ Quick iterations

For production SaaS, consider:
- React/Next.js frontend
- FastAPI/Flask backend
- Database storage
- User authentication
- Cloud deployment
