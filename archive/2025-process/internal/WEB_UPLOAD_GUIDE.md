# Web Upload Guide - No Git Commands Needed

If you can't create repos but can upload files via GitLab web interface:

## Minimal File Set (5 files)

These are the essential files to upload:

1. **mangrove_workflow.ipynb** - The main demo
2. **README.md** - Rename OSPD_WIKI_ENTRY.md to this
3. **MANGROVE_CVI_INTEGRATION.md** - Your integration scenario
4. **requirements.txt** - Dependencies list
5. **test_notebook.py** - Validation script

## Upload Steps

### Step 1: Navigate to OSPD-2025
Go to: https://gitlab.ogc.org/ogc/OSPD-2025

### Step 2: Create Your Folder

**If you can create directories:**
- Click "+" button
- Select "New directory"
- Name it `D011` (or next available number)
- Create

**If you can't create directories:**
Ask an admin or upload to existing location they suggest.

### Step 3: Upload Files

For each file:
1. Navigate into your D011 folder
2. Click "+" → "Upload file"
3. Select file from: `/Users/cameronsajedi/code/MCP/OGC/mangrove/ospd-mangrove-demo/`
4. Add commit message: "Add [filename]"
5. Commit changes

### Step 4: Rename OSPD_WIKI_ENTRY.md

After uploading OSPD_WIKI_ENTRY.md:
1. Click the file
2. Click "Edit" or rename button
3. Change name to: `README.md`
4. Commit with message: "Rename to README"

## Alternative: Single Compressed Upload

If uploading individual files is too slow:

```bash
# Create archive of key files
cd /Users/cameronsajedi/code/MCP/OGC/mangrove/ospd-mangrove-demo

# Create minimal package
tar -czf mangrove-ospd.tar.gz \
  mangrove_workflow.ipynb \
  OSPD_WIKI_ENTRY.md \
  MANGROVE_CVI_INTEGRATION.md \
  requirements.txt \
  test_notebook.py \
  DEMO_GUIDE.md \
  config/
```

Then upload mangrove-ospd.tar.gz and extract on the web interface (if supported).

## What People Need to Know

After upload, tell participants:

**Location:**
"My demonstrator is in the OSPD-2025 repository under D011"

**How to Run:**
```bash
git clone https://gitlab.ogc.org/ogc/OSPD-2025.git
cd OSPD-2025/D011
pip install -r requirements.txt
jupyter lab mangrove_workflow.ipynb
```

**Key Files:**
- README.md: Full description
- MANGROVE_CVI_INTEGRATION.md: Coastal integration scenario
- test_notebook.py: Pre-flight check

## Backup Plan: Share Your Local Repo Link

If GitLab upload is too difficult, you can:

1. Keep working locally
2. During presentation, say: "Code available on request"
3. After presentation, email zip file to interested parties
4. Or: Upload to GitHub as fallback and share that link

## The Absolute Minimum

If you're really pressed for time, just upload these TWO files:

1. **mangrove_workflow.ipynb**
2. **README.md** (the renamed OSPD_WIKI_ENTRY.md)

This gives people:
- The working demo
- Complete documentation

Everything else is supplementary.
