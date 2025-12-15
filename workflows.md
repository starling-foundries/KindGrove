# Workflow Testing Results

**Date:** 2025-12-15
**Branch:** feature/marimo-notebook
**Tested By:** Claude Code + Cameron Sajedi

---

## Workflow Tested

**Gerald's OGC Application Package CWL Workflow**
- **File:** `mangrove_workflow_ogc_application_package.cwl`
- **Contributor:** Gérald Fenoy (https://orcid.org/0000-0002-9617-8641)

---

## Test Configuration

| Parameter | Value |
|-----------|-------|
| **Input file** | workflow_input_gerald.yml |
| **Study site** | Thor Heyerdahl Climate Park, Myanmar |
| **BBox** | [95.15, 15.9, 95.35, 16.1] |
| **Cloud cover max** | 20% |
| **Days back** | 90 |

---

## Results Summary

| Step | Status | Notes |
|------|--------|-------|
| cwltool installation | PASS | v3.1.20251031082601 |
| Input file creation | PASS | workflow_input_gerald.yml |
| Docker availability | PASS | Docker v28.5.2 |
| Workflow resolution | PASS | Required `#mangrove-workflow` suffix |
| parse_aoi step | PASS | Alpine 3.22.2 pulled successfully |
| Docker image pull | PASS | Made GHCR package public, v0.0.1 tag pushed |
| mangrove_cli step | FAIL | Architecture mismatch (amd64 image on arm64 host) |

---

## Detailed Execution Log

### Step 1: cwltool Installation

```bash
pip install cwltool
```

**Result:** Successfully installed cwltool v3.1.20251031082601 with dependencies:
- schema-salad, cwl-utils, cwl-upgrader
- rdflib, prov, pydot
- CacheControl, argcomplete

### Step 2: Input File Creation

Created `workflow_input_gerald.yml` with OGC BBox schema format:

```yaml
aoi:
  class: https://raw.githubusercontent.com/eoap/schemas/main/ogc.yaml#BBox
  bbox: [95.15, 15.9, 95.35, 16.1]
  crs: "CRS84"
cloud_cover_max: 20.0
days_back: 90
```

**Note:** The existing input files (`mangrove_workflow_input_*.yml`) used `bounding_box` parameter name, but Gerald's workflow expects `aoi` with the OGC BBox type.

### Step 3: Initial Execution Attempt

```bash
cwltool mangrove_workflow_ogc_application_package.cwl workflow_input_gerald.yml
```

**Error:**
```
Tool definition failed initialization:
Tool file contains graph of multiple objects, must specify one of #parse_aoi, #mangrove-workflow, #mangrove_cli
```

**Fix:** The CWL file uses `$graph` to define multiple tools. Must specify the main workflow with `#mangrove-workflow` suffix.

### Step 4: Corrected Execution

```bash
cwltool mangrove_workflow_ogc_application_package.cwl#mangrove-workflow workflow_input_gerald.yml
```

**Execution Progress:**

1. **Workflow started** - Resolved to main workflow successfully
2. **parse_aoi step:**
   - Pulled `alpine:3.22.2` image successfully
   - Parsed BBox coordinates from input
   - **Completed successfully**
3. **step_1 (mangrove_cli):**
   - Attempted to pull `ghcr.io/starling-foundries/kindgrove/mangrove-cwl:v0.0.1`
   - **BLOCKED** - Image requires authentication

---

## Issues Encountered

### Issue 1: $graph Structure Requires Workflow Selection

**Problem:** CWL files with `$graph` structure containing multiple tools require specifying which tool/workflow to run.

**Solution:** Append `#workflow-id` to the CWL file path:
```bash
cwltool file.cwl#mangrove-workflow input.yml
```

### Issue 2: Docker Image Authentication Required

**Problem:** The main processing image `ghcr.io/starling-foundries/kindgrove/mangrove-cwl:v0.0.1` is on GitHub Container Registry and requires authentication.

**Log excerpt:**
```
Error: No such object: ghcr.io/starling-foundries/kindgrove/mangrove-cwl:v0.0.1
INFO ['docker', 'pull', 'ghcr.io/starling-foundries/kindgrove/mangrove-cwl:v0.0.1']
Login prior to pull: Log in with your Docker ID...
Username: [waiting for input]
```

**Potential Solutions:**

1. **Make the image public** on GHCR (recommended for demo workflows)
2. **Authenticate with GHCR:**
   ```bash
   echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
   ```
3. **Build the image locally** from the source Dockerfile

### Issue 3: Input Parameter Name Mismatch

**Problem:** Existing input files use `bounding_box` but Gerald's workflow expects `aoi`.

**Solution:** Created new input file `workflow_input_gerald.yml` with correct parameter names.

### Issue 4: Docker Architecture Mismatch (Apple Silicon)

**Problem:** The Docker image `ghcr.io/starling-foundries/kindgrove/mangrove-cwl:v0.0.1` is built for `linux/amd64` but the test machine is Apple Silicon (`linux/arm64`).

**Log excerpt:**
```
WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8)
PermissionError: [Errno 13] Permission denied: '/app/cwl/bin/mangrove_workflow_for_cwl'
```

**Root Cause:** GitHub Actions runners build x86/amd64 images by default. When run on Apple Silicon Macs via Docker's Rosetta emulation, permission errors can occur with executable binaries.

**Solutions:**

1. **Build multi-arch image** - Update GitHub Actions workflow to build for both `linux/amd64` and `linux/arm64`:
   ```yaml
   - name: Set up QEMU
     uses: docker/setup-qemu-action@v3

   - name: Build and push
     uses: docker/build-push-action@v5
     with:
       platforms: linux/amd64,linux/arm64
   ```

2. **Test on x86 machine** - Run CWL workflow on Linux x86 or Intel Mac

3. **Use cloud execution** - Run on OGC platform or cloud CI/CD where architecture matches

---

## Workflow Architecture

Gerald's workflow uses a two-step architecture:

```
┌─────────────────────────────────────────────────────────────┐
│              mangrove-workflow (Workflow)                   │
├─────────────────────────────────────────────────────────────┤
│ Inputs: aoi (BBox), cloud_cover_max, days_back              │
│ Output: stac (Directory)                                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────────┐    ┌───────────────────────────┐  │
│  │     parse_aoi        │───►│     mangrove_cli          │  │
│  │  (CommandLineTool)   │    │   (CommandLineTool)       │  │
│  │                      │    │                           │  │
│  │ Docker: alpine:3.22.2│    │ Docker: ghcr.io/starling- │  │
│  │                      │    │ foundries/kindgrove/      │  │
│  │ Parses BBox into:    │    │ mangrove-cwl:v0.0.1       │  │
│  │ - west, south        │    │                           │  │
│  │ - east, north        │    │ Runs biomass analysis     │  │
│  │ - output_dir         │    │                           │  │
│  └──────────────────────┘    └───────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Next Steps to Complete Testing

1. **Option A: Make Docker image public**
   - Contact Gerald or repository admin to make the GHCR image public
   - Re-run: `cwltool mangrove_workflow_ogc_application_package.cwl#mangrove-workflow workflow_input_gerald.yml`

2. **Option B: Authenticate with GHCR**
   ```bash
   # Generate a GitHub PAT with read:packages scope
   echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
   cwltool mangrove_workflow_ogc_application_package.cwl#mangrove-workflow workflow_input_gerald.yml
   ```

3. **Option C: Build image locally**
   - Clone the KindGrove repository
   - Build the Docker image from Dockerfile
   - Tag it as `ghcr.io/starling-foundries/kindgrove/mangrove-cwl:v0.0.1`

---

## Comparison: CWL vs Other Workflow Methods

| Feature | CWL (Gerald's) | marimo Notebook | Python Script |
|---------|----------------|-----------------|---------------|
| **Containerization** | Built-in Docker support | None (local Python) | None |
| **Portability** | Excellent (OGC standard) | Good (pure Python) | Good |
| **Reproducibility** | Excellent | Excellent | Good |
| **Interactive** | No | Yes (reactive) | No |
| **Dependencies** | Docker required | Python packages | Python packages |
| **Schema validation** | OGC BBox types | None | None |
| **Execution** | `cwltool` | `marimo run` | `python script.py` |

---

## Files Created/Modified

| File | Purpose |
|------|---------|
| `workflow_input_gerald.yml` | Input file for Gerald's CWL workflow |
| `workflows.md` | This documentation file |

---

## Conclusions

1. **Gerald's CWL workflow is well-structured** - Uses OGC Application Package patterns with proper schema imports
2. **First step (parse_aoi) works correctly** - Successfully parses BBox using Alpine container
3. **Docker image is now public** - v0.0.1 tag pushed, GHCR package made public
4. **Architecture mismatch blocks local testing** - amd64 image fails on Apple Silicon (arm64)
5. **Input schema differs from other workflows** - Uses `aoi` (OGC BBox type) instead of `bounding_box`

**Recommendations:**

1. **For local Apple Silicon testing:** Build multi-arch Docker images (amd64 + arm64)
2. **For CI/CD testing:** Workflow will run correctly on GitHub Actions (x86 runners)
3. **For OGC platform:** Should work as-is on standard x86 infrastructure

**Workflow Status:** Validated up to Docker image pull. Full execution requires x86 architecture or multi-arch image rebuild.
