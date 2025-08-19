# In Python, load your new projections and test
import pandas as pd

# Load the projections we just created
projections = pd.read_csv("simple_projections.csv")

# Check the data looks good
print("Sample projections:")
print(projections.head())
print(f"Shape: {projections.shape}")
print(f"QB projections range: {projections[projections['pos']=='QB']['proj_points'].min()} to {projections[projections['pos']=='QB']['proj_points'].max()}")