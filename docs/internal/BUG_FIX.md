# Bug Fix for Sentinel-2 Data Loading

## The Problem
You're getting this error:
```
ValueError: Cannot pick a common CRS, since asset 'red' of item 0 'S2B_46QFD_20250218_0_L2A' does not have one.
Please specify a CRS with the `epsg=` argument.
```

## Quick Fix

In the notebook, find this line in Section 2 (the `on_search_click` function):

```python
sentinel2_data = stackstac.stack(
    [best_item],
    assets=['red', 'green', 'blue', 'nir', 'rededge1', 'rededge2', 'rededge3'],
    bounds=bbox,
    resolution=10,
    chunksize=(1, 1, 512, 512)
)
```

Change it to:

```python
sentinel2_data = stackstac.stack(
    [best_item],
    assets=['red', 'green', 'blue', 'nir', 'rededge1', 'rededge2', 'rededge3'],
    bounds=bbox,
    epsg=4326,  # ADD THIS LINE - WGS84 coordinate system
    resolution=10,
    chunksize=(1, 1, 512, 512)
)
```

Just add the line `epsg=4326,` after the `bounds=bbox,` line.

## How to Apply the Fix

### Option 1: Edit in Jupyter (Easiest)
1. In Jupyter, click on Section 2 cell (the one with the long `on_search_click` function)
2. Find the `stackstac.stack(` call (around line 89 of that cell)
3. Add `epsg=4326,` after the `bounds=bbox,` line
4. Run the cell again (Shift+Enter)

### Option 2: Copy-Paste Fixed Function
Create a new cell RIGHT AFTER Section 2 and paste this:

```python
# Bug fix: Redefine the search function with epsg parameter
def on_search_click_fixed(b):
    global sentinel2_items, sentinel2_data

    with search_output:
        clear_output(wait=True)

        if selected_bounds is None:
            print("❌ Please initialize a study area first!")
            return

        print("🔍 Searching AWS STAC catalog...")

        catalog = Client.open("https://earth-search.aws.element84.com/v1")
        bounds = selected_bounds
        bbox = [bounds['west'], bounds['south'], bounds['east'], bounds['north']]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back_slider.value)

        search = catalog.search(
            collections=["sentinel-2-l2a"],
            bbox=bbox,
            datetime=f"{start_date.isoformat()}/{end_date.isoformat()}",
            query={"eo:cloud_cover": {"lt": cloud_cover_slider.value}}
        )

        items = list(search.items())
        sentinel2_items = items

        if len(items) == 0:
            print(f"❌ No scenes found with <{cloud_cover_slider.value}% cloud cover")
            print("💡 Try increasing the cloud cover threshold or date range")
            return

        print(f"✅ Found {len(items)} Sentinel-2 scenes")

        scene_data = []
        for item in items[:10]:
            scene_data.append({
                'Date': item.datetime.strftime('%Y-%m-%d'),
                'Cloud %': f"{item.properties.get('eo:cloud_cover', 'N/A'):.1f}",
                'ID': item.id[:30] + '...'
            })

        df = pd.DataFrame(scene_data)
        display(df)

        best_item = min(items, key=lambda x: x.properties.get('eo:cloud_cover', 100))
        print(f"\n📥 Loading best scene: {best_item.datetime.strftime('%Y-%m-%d')}")
        print(f"   Cloud cover: {best_item.properties.get('eo:cloud_cover', 'N/A'):.1f}%")

        # FIXED: Added epsg=4326
        sentinel2_data = stackstac.stack(
            [best_item],
            assets=['red', 'green', 'blue', 'nir', 'rededge1', 'rededge2', 'rededge3'],
            bounds=bbox,
            epsg=4326,  # WGS84 coordinate system
            resolution=10,
            chunksize=(1, 1, 512, 512)
        )

        print(f"✅ Data loaded: {sentinel2_data.shape}")
        print(f"   Bands: {list(sentinel2_data.band.values)}")
        print("\n📍 Proceed to mangrove detection")

# Replace the button's click handler
search_button.on_click(on_search_click_fixed)
print("✅ Bug fix applied! Try searching for Sentinel-2 data again.")
```

Then run that cell and try the "Search Sentinel-2 Data" button again.

## Why This Happens

Sentinel-2 data from different sources sometimes doesn't include coordinate system metadata. By explicitly setting `epsg=4326` (the standard WGS84 lat/lon system), we tell stackstac what coordinate system to use.

## Testing the Fix

After applying the fix:
1. Go back to Section 1, click "Initialize Study Area"
2. Go to Section 2, click "Search Sentinel-2 Data"
3. Should now work without the CRS error

If it still errors, that's OK - the notebook will work with synthetic data in the next sections.
