# Installation Guide for OSPD Mangrove Demonstrator

## 🚀 Quick Start (Minimal Installation)

If you encounter issues with the full requirements, use the minimal version:

```bash
pip install -r requirements-minimal.txt
```

This installs only the essential packages including `rhealpixdggs` which is the core requirement.

## 📦 Package Installation Options

### Option 1: Full Installation (Recommended)
```bash
pip install -r requirements.txt
```

This includes all packages for cloud-optimized Sentinel-2 access.

### Option 2: Minimal Installation
```bash
pip install -r requirements-minimal.txt
```

Use this if you have issues with:
- `zarr`, `kerchunk` (Pangeo stack)
- `stackstac`, `odc-stac` (STAC libraries)
- `rasterio`, `rioxarray` (Geospatial I/O)

### Option 3: Conda Environment
```bash
conda env create -f environment.yml
conda activate mangrove-demo
```

## 🔧 Troubleshooting

### Issue: `rhealpixdggs-py` not found
**Solution**: The correct package name is `rhealpixdggs` (without `-py`):
```bash
pip install rhealpixdggs>=0.5.5
```

### Issue: STAC packages not available
**Solution**: The demo includes synthetic data fallback. You can run it without STAC packages, though you won't get live Sentinel-2 data.

### Issue: Rasterio installation fails
**Solution**: Rasterio requires GDAL. On macOS:
```bash
brew install gdal
pip install rasterio
```

On Ubuntu/Debian:
```bash
sudo apt-get install gdal-bin libgdal-dev
pip install rasterio
```

### Issue: Kerchunk/Zarr not available
**Solution**: These are optional for the Pangeo stack optimization. The demo can run without them using the synthetic data mode.

## ✅ Verify Installation

Run the test script to check your installation:
```bash
python test_installation.py
```

### Minimum Required Packages
The demo absolutely requires:
- ✅ `rhealpixdggs` - Core rHEALPix functionality
- ✅ `numpy`, `pandas` - Data processing
- ✅ `geopandas` - Spatial operations
- ✅ `matplotlib` or `folium` - Visualization

### Optional but Recommended
- 🔸 `xarray` - Better array handling
- 🔸 `zarr`, `kerchunk` - Cloud-optimized data access
- 🔸 `stackstac` - Sentinel-2 data loading
- 🔸 `plotly` - Interactive visualizations

## 🏃 Running the Demo

### With Full Installation
The notebook will automatically:
1. Search for live Sentinel-2 data
2. Load imagery using Pangeo tools
3. Process with rHEALPix cells
4. Estimate mangrove biomass

### With Minimal Installation
The notebook will:
1. Use synthetic NDVI data (realistic patterns)
2. Process with rHEALPix cells (same as full version)
3. Estimate biomass (same model)
4. Demonstrate platform independence (key feature!)

## 💡 Platform-Specific Notes

### Google Colab
```python
!pip install rhealpixdggs geopandas folium
```

### i-Guide Platform
Should have most geospatial packages pre-installed. Just add:
```bash
pip install rhealpixdggs
```

### AWS SageMaker
Use the conda environment file for best compatibility:
```bash
conda env create -f environment.yml
```

## 📞 Support

If you encounter issues:
1. Check the test script: `python test_installation.py`
2. Try the minimal requirements: `pip install -r requirements-minimal.txt`
3. The demo works with synthetic data if Sentinel-2 packages fail
4. The key innovation (rHEALPix cells) works regardless!

Remember: The core demonstration of **platform-independent spatial cells** works with just the minimal installation!
