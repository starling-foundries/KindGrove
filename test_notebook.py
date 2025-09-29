#!/usr/bin/env python
"""
Quick test script to validate notebook functionality without running full workflow
"""

import sys
import numpy as np
import pandas as pd

print("🧪 Testing Notebook Dependencies...")
print("=" * 50)

# Test 1: Core scientific libraries
try:
    import numpy as np
    import pandas as pd
    import xarray as xr
    print("✅ Core libraries (numpy, pandas, xarray)")
except ImportError as e:
    print(f"❌ Core libraries: {e}")
    sys.exit(1)

# Test 2: Geospatial libraries
try:
    import geopandas as gpd
    from shapely.geometry import Point, box
    print("✅ Geospatial libraries (geopandas, shapely)")
except ImportError as e:
    print(f"❌ Geospatial libraries: {e}")
    sys.exit(1)

# Test 3: STAC and satellite data
try:
    from pystac_client import Client
    import stackstac
    import rioxarray
    print("✅ STAC libraries (pystac_client, stackstac, rioxarray)")
except ImportError as e:
    print(f"⚠️  STAC libraries: {e}")
    print("   Notebook will use demo mode")

# Test 4: Visualization
try:
    import plotly.graph_objects as go
    import plotly.express as px
    print("✅ Plotly visualization")
except ImportError as e:
    print(f"❌ Plotly: {e}")
    sys.exit(1)

# Test 5: Interactive widgets
try:
    import ipywidgets as widgets
    from IPython.display import display
    print("✅ Jupyter widgets (ipywidgets)")
except ImportError as e:
    print(f"❌ Jupyter widgets: {e}")
    sys.exit(1)

# Test 6: Generate synthetic test data
print("\n🔬 Testing Data Generation...")
try:
    # Create synthetic mangrove data
    grid_size = 50
    lons = np.linspace(94.7, 94.8, grid_size)
    lats = np.linspace(16.7, 16.8, grid_size)
    lon_grid, lat_grid = np.meshgrid(lons, lats)

    # Synthetic NDVI
    np.random.seed(42)
    ndvi = 0.6 + 0.2 * np.sin(lon_grid * 100) * np.cos(lat_grid * 100)
    ndvi += np.random.normal(0, 0.05, lon_grid.shape)
    ndvi = np.clip(ndvi, 0.2, 0.9)

    # Biomass calculation
    biomass = 250.5 * ndvi - 75.2
    biomass = np.maximum(biomass, 0)

    print(f"✅ Generated {grid_size}x{grid_size} synthetic grid")
    print(f"   NDVI range: {ndvi.min():.3f} - {ndvi.max():.3f}")
    print(f"   Biomass range: {biomass.min():.1f} - {biomass.max():.1f} Mg/ha")
    print(f"   Mean biomass: {biomass.mean():.1f} Mg/ha")

except Exception as e:
    print(f"❌ Data generation failed: {e}")
    sys.exit(1)

# Test 7: Visualization capability
print("\n📊 Testing Visualization...")
try:
    # Create test contour plot
    fig = go.Figure(data=go.Contour(
        z=biomass,
        x=lons,
        y=lats,
        colorscale='Viridis',
        contours=dict(
            start=0,
            end=200,
            size=20,
            showlabels=True
        )
    ))

    fig.update_layout(
        title='Test Isopleth Map',
        height=400
    )

    print("✅ Plotly contour (isopleth) visualization working")

except Exception as e:
    print(f"❌ Visualization failed: {e}")
    sys.exit(1)

# Test 8: STAC connectivity (optional)
print("\n🌐 Testing STAC Connection...")
try:
    from pystac_client import Client
    catalog = Client.open("https://earth-search.aws.element84.com/v1")
    print(f"✅ Connected to AWS STAC catalog")
    print(f"   Catalog ID: {catalog.id}")
except Exception as e:
    print(f"⚠️  STAC connection: {e}")
    print("   Notebook will use demo mode with synthetic data")

print("\n" + "=" * 50)
print("🎉 All critical tests passed!")
print("\n📋 Summary:")
print("   ✅ All required dependencies installed")
print("   ✅ Data generation working")
print("   ✅ Visualization functional")
print("   ✅ Ready to run notebook")
print("\n💡 Next steps:")
print("   1. Open: jupyter lab mangrove_workflow.ipynb")
print("   2. Run cells sequentially")
print("   3. Follow interactive workflow")