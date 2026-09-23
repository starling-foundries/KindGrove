# stac-fingerprint: two targets from one file. Build from the REPOSITORY ROOT (the pystac module lives in stac-extension/):
#   docker build -f cwl/Dockerfile --target slim   -t ghcr.io/starling-foundries/stac-fingerprint:0.3.0 .
#   docker build -f cwl/Dockerfile --target raster -t ghcr.io/starling-foundries/stac-fingerprint:0.3.0-raster .
#   slim    python + the burin-core wheel + pystac + pystac_fingerprint. Geometry fingerprints. ~220 MB.
#   raster  + rasterio (and numpy) for --assets auto|k1,k2 on GeoTIFF mask assets. ~480 MB.
FROM python:3.12-slim AS slim
WORKDIR /app
COPY cwl/wheels/ /wheels/
# pick the wheel for the image architecture (both arm64 and x86_64 wheels may sit in wheels/)
RUN pip install --no-cache-dir /wheels/burin_core-*manylinux*"$(uname -m)"*.whl pystac \
    && rm -rf /wheels
COPY stac-extension/python/pystac_fingerprint.py /app/pystac_fingerprint.py
COPY cwl/fingerprint.py /app/fingerprint.py
ENV PYTHONPATH=/app
# No ENTRYPOINT: CWL supplies the full command (baseCommand), as the OGC quickwin pattern expects.
CMD ["python", "/app/fingerprint.py", "--help"]

FROM slim AS raster
# rasterio's manylinux wheel links libexpat, which python:*-slim does not ship
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir rasterio numpy
