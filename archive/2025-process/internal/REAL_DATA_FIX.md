# Real Data Solution with Progress Tracking

## The Problem
Sentinel-2 data loading hangs at "Calculating vegetation indices" because stackstac creates lazy arrays that don't download until you access them. No visual feedback makes it seem stuck.

## Solution: Pre-compute with Progress + Cache

This gives you real data with visual confirmation of progress.

## Implementation

### Step 1: Replace Section 2 Cell

Replace the entire `on_search_click` function in Section 2 with this version:

```python
def on_search_click(b):
    global sentinel2_items, sentinel2_data

    with search_output:
        clear_output(wait=True)

        if selected_bounds is None:
            print("❌ Please initialize a study area first!")
            return

        print("🔍 Searching AWS STAC catalog...")

        # Connect to AWS STAC catalog
        catalog = Client.open("https://earth-search.aws.element84.com/v1")

        # Define search parameters
        bounds = selected_bounds
        bbox = [bounds['west'], bounds['south'], bounds['east'], bounds['north']]

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back_slider.value)

        # Search for Sentinel-2 L2A scenes
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

        # Create summary DataFrame
        scene_data = []
        for item in items[:10]:
            scene_data.append({
                'Date': item.datetime.strftime('%Y-%m-%d'),
                'Cloud %': f"{item.properties.get('eo:cloud_cover', 'N/A'):.1f}",
                'ID': item.id[:30] + '...'
            })

        df = pd.DataFrame(scene_data)
        display(df)

        # Load the best scene (lowest cloud cover)
        best_item = min(items, key=lambda x: x.properties.get('eo:cloud_cover', 100))
        print(f"\n📥 Loading scene: {best_item.datetime.strftime('%Y-%m-%d')}")
        print(f"   Cloud cover: {best_item.properties.get('eo:cloud_cover', 'N/A'):.1f}%")

        # Check for cached data first
        cache_file = 'sentinel2_cache.npz'
        cache_exists = False
        try:
            import os
            if os.path.exists(cache_file):
                print(f"\n💾 Found cached data from previous run")
                cached = np.load(cache_file)

                # Reconstruct xarray from cache
                sentinel2_data = xr.DataArray(
                    np.stack([cached['red'], cached['green'], cached['nir']]),
                    dims=['band', 'y', 'x'],
                    coords={'band': ['red', 'green', 'nir']}
                )
                cache_exists = True
                print(f"✅ Loaded from cache (instant)")
        except:
            pass

        if not cache_exists:
            print(f"\n⏳ Downloading data from AWS...")
            print(f"   This will take 30-60 seconds on first run")
            print(f"   Progress: ", end='', flush=True)

            # Create lazy stack (only red, green, nir - we don't use others)
            sentinel2_lazy = stackstac.stack(
                [best_item],
                assets=['red', 'green', 'nir'],  # Only bands we actually use
                bounds=bbox,
                epsg=4326,
                resolution=10,
                chunksize=(1, 1, 512, 512)
            )

            # Force compute with progress indicator
            import time
            start_time = time.time()

            # Show progress dots while computing
            import threading
            computing = True
            def show_progress():
                while computing:
                    print('.', end='', flush=True)
                    time.sleep(2)

            progress_thread = threading.Thread(target=show_progress)
            progress_thread.start()

            try:
                # This is where actual download happens
                sentinel2_data = sentinel2_lazy.compute()
                computing = False
                progress_thread.join()

                elapsed = time.time() - start_time
                print(f"\n✅ Data downloaded in {elapsed:.1f} seconds")

                # Cache for next time
                print(f"💾 Caching data for future runs...")
                np.savez_compressed(
                    cache_file,
                    red=sentinel2_data.sel(band='red').values,
                    green=sentinel2_data.sel(band='green').values,
                    nir=sentinel2_data.sel(band='nir').values
                )
                print(f"✅ Cached to {cache_file}")

            except Exception as e:
                computing = False
                progress_thread.join()
                print(f"\n❌ Download failed: {e}")
                print("This can happen with network issues or AWS throttling")
                return

        print(f"\n📊 Data ready: {sentinel2_data.shape}")
        print(f"   Bands: {list(sentinel2_data.band.values)}")
        print("\n📍 Proceed to mangrove detection")

search_button.on_click(on_search_click)
```

### Step 2: Also Update Section 3 (Detection)

The `calculate_indices` function needs adjustment since we only have 3 bands now:

```python
def calculate_indices(data):
    """Calculate vegetation indices for mangrove detection"""
    # Extract bands (we only loaded red, green, nir)
    if len(data.shape) == 3:  # From cache or computed
        red = data.sel(band='red').values
        green = data.sel(band='green').values
        nir = data.sel(band='nir').values
    else:  # From stackstac (has time dimension)
        red = data.sel(band='red').values[0]
        green = data.sel(band='green').values[0]
        nir = data.sel(band='nir').values[0]

    # NDVI - Normalized Difference Vegetation Index
    ndvi = (nir - red) / (nir + red + 1e-8)

    # NDWI - Normalized Difference Water Index
    ndwi = (green - nir) / (green + nir + 1e-8)

    # SAVI - Soil Adjusted Vegetation Index
    L = 0.5
    savi = ((nir - red) / (nir + red + L)) * (1 + L)

    return {
        'ndvi': ndvi,
        'ndvi': ndvi,
        'savi': savi
    }
```

## What This Does

### First Run (Tonight - Pre-Demo)
1. Searches STAC catalog (instant)
2. Downloads data from AWS with progress dots: `......`
3. Takes 30-60 seconds (you'll see it working)
4. Saves to `sentinel2_cache.npz` (real data, ~15 MB file)
5. Shows elapsed time

### Demo Tomorrow
1. Searches STAC catalog (instant)
2. Finds cached data
3. Loads from disk (instant - under 1 second)
4. Shows "Loaded from cache"

## Visual Confirmation

You'll see:
```
⏳ Downloading data from AWS...
   This will take 30-60 seconds on first run
   Progress: ...........
✅ Data downloaded in 34.2 seconds
💾 Caching data for future runs...
✅ Cached to sentinel2_cache.npz
```

If it stalls, you'll see dots stop appearing. If dots keep coming, it's working.

## On Demo Day Decision Tree

**If you run the notebook fresh:**
- Dots appearing? → Let it cook (30-60 sec)
- Dots stopped? → Kill it, use cached version from tonight

**If cache exists:**
- Loads instantly, no waiting

## Testing Tonight

1. Apply the fix above
2. Run Section 2 "Search Sentinel-2 Data"
3. Watch the progress dots
4. When done, you'll have `sentinel2_cache.npz` file
5. Run Sections 3-5 to complete workflow
6. Tomorrow: Same data loads instantly

## Removing Cache (If Needed)

To force fresh download:
```bash
rm sentinel2_cache.npz
```

Then run Section 2 again.

## Why This Works

- Real Sentinel-2 data (not fake)
- Visual progress (not a hang)
- Fast demo (cached)
- Network independent (after first run)
- You can show the cache file and explain it's real AWS data

This is how production systems work - data lakes with local caching.
