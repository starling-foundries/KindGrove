# GitLab Repository Setup Instructions

## Prerequisites
- Git repository initialized (already complete)
- GitLab account with project created
- SSH key or HTTPS credentials configured

## Quick Push to GitLab

### Step 1: Add GitLab Remote

Replace `<your-gitlab-url>` with your actual GitLab repository URL:

```bash
cd /Users/cameronsajedi/code/MCP/OGC/mangrove/ospd-mangrove-demo
git remote add origin <your-gitlab-url>
```

Example:
```bash
git remote add origin git@gitlab.com:username/ospd-mangrove-demo.git
```

### Step 2: Verify Remote

```bash
git remote -v
```

Should show:
```
origin  <your-gitlab-url> (fetch)
origin  <your-gitlab-url> (push)
```

### Step 3: Push to GitLab

```bash
git push -u origin main
```

If you encounter authentication issues with HTTPS:
```bash
git push -u origin main --verbose
```

### Step 4: Verify Upload

Visit your GitLab repository URL in browser and confirm files are visible.

## Repository Contents Being Uploaded

### Core Files (11 commits)
- Initial project structure
- Research literature foundation
- Dependency management and testing
- Site configuration
- Main workflow notebook
- Comprehensive documentation
- Launch utilities
- Interactive validation framework
- Development history archive
- Reference sites and validation comparison
- Alternative installation methods

### Documentation Files
- README.md (main landing page)
- QUICKSTART.md (user guide)
- WORKFLOW_README.md (technical details)
- DEMO_GUIDE.md (presentation walkthrough)
- OSPD_WIKI_ENTRY.md (for GitLab wiki)
- VALIDATION_SESSION.md (human review checklist)
- VALIDATION_COMPARISON.md (literature validation)
- MANGROVE_CVI_INTEGRATION.md (coastal integration scenario)
- INSTALLATION_GUIDE.md (setup instructions)
- OBSOLETE_NOTEBOOKS.md (development log)

### Configuration
- config/demo_config.yaml (site definitions)
- config/reference_sites.yaml (validation sites)

### Code and Testing
- mangrove_workflow.ipynb (main notebook)
- test_notebook.py (dependency validation)
- launch.sh (quick start script)
- requirements.txt (Python dependencies)
- environment.yml (Conda environment)

### Archive
- archive/notebooks/ (7 development iterations)

## GitLab Wiki Setup

### Option 1: Web Interface

1. Navigate to your GitLab project
2. Sidebar: Wiki
3. Click "Create your first page"
4. Title: "Mangrove Biomass Estimation OSPD"
5. Copy contents of OSPD_WIKI_ENTRY.md into editor
6. Click "Create page"

### Option 2: Command Line (if wiki repo access enabled)

```bash
# Clone wiki repository
git clone git@gitlab.com:username/ospd-mangrove-demo.wiki.git
cd ospd-mangrove-demo.wiki

# Create wiki page
cp ../ospd-mangrove-demo/OSPD_WIKI_ENTRY.md home.md

# Commit and push
git add home.md
git commit -m "Add mangrove OSPD wiki entry"
git push origin master
```

## Post-Upload Checklist

- [ ] Verify README.md displays correctly on repository landing page
- [ ] Confirm all 11 commits visible in history
- [ ] Check that DEMO_GUIDE.md renders properly
- [ ] Verify MANGROVE_CVI_INTEGRATION.md formatting
- [ ] Test launch.sh download and execution (if possible)
- [ ] Create wiki entry from OSPD_WIKI_ENTRY.md
- [ ] Add repository URL to presentation materials
- [ ] Update citation in OSPD_WIKI_ENTRY.md with actual GitLab URL

## Sharing with OSPD Participants

### For Coastal Vulnerability Team

Direct them to:
1. **Integration scenario**: MANGROVE_CVI_INTEGRATION.md
2. **Key insight**: Dual-output framework (carbon + coastal protection)
3. **Data compatibility**: GeoJSON transect format compatible
4. **Quick win**: Add ecosystem protection as 5th CVI parameter

Talking points:
- "We've mapped mangrove biomass with spatial resolution compatible with your CVI transects"
- "Research shows 60-70% wave height reduction through mature mangrove forests"
- "Economic protection value: $5,000-$26,000 per hectare per year depending on region"
- "Dual assessment: carbon sequestration AND coastal protection in single workflow"

### For Other OSPD Participants

Highlight:
1. **Open data approach**: No API keys, no authentication barriers
2. **OGC compliance**: STAC catalog, GeoJSON outputs
3. **Validation framework**: Compared against 5 published studies
4. **Reproducibility**: Complete documentation, tested dependencies
5. **Integration potential**: Spatial data products compatible with other workflows

## Repository URL Format

Update these files with actual URL after push:

1. README.md line 220: Replace `https://github.com/[your-repo]`
2. OSPD_WIKI_ENTRY.md line 402: Add actual GitLab URL

Search and replace:
```bash
grep -r "your-repo\|GitLab URL" *.md
```

Then manually update each occurrence with:
```
https://gitlab.com/username/ospd-mangrove-demo
```

## Troubleshooting

### Large File Warning
If Git warns about large files (archive/notebooks/ contains ~47MB):
```bash
# Check file sizes
du -sh archive/notebooks/*

# If needed, use Git LFS for large notebooks
git lfs track "*.ipynb"
git add .gitattributes
git commit -m "Add Git LFS tracking for notebooks"
```

### Authentication Issues
If push fails with authentication error:

**For SSH:**
```bash
ssh -T git@gitlab.com
```

**For HTTPS:**
Generate personal access token in GitLab settings and use as password.

### Commit History Not Showing
If commits appear squashed:
```bash
git log --oneline --graph --decorate
```

Verify 11 commits locally before troubleshooting remote.

## Complete Command Sequence

Copy-paste ready:

```bash
# Navigate to repository
cd /Users/cameronsajedi/code/MCP/OGC/mangrove/ospd-mangrove-demo

# Verify local state
git status
git log --oneline

# Add remote (replace URL)
git remote add origin <your-gitlab-url>

# Push
git push -u origin main

# Verify
git remote -v
```

Done. Repository now accessible to OSPD participants.
