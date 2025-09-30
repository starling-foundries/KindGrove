# Contributing to KindGrove

This repository is part of the OGC 2025 Open Science Platform Demonstrator series and serves as a reference implementation for mangrove biomass estimation workflows.

## Purpose

KindGrove demonstrates:
- Open data architecture using STAC and AWS Open Data Registry
- Validated scientific methods for mangrove monitoring
- Consilience approach for multi-sensor integration
- Integration pathways with coastal vulnerability assessments

## How to Contribute

### Reporting Issues

If you encounter problems running the workflow:
1. Check that all dependencies from `requirements.txt` are installed
2. Ensure you have internet access for AWS STAC catalog queries
3. Open an issue describing the problem, including your Python version and error messages

### Suggesting Improvements

We welcome suggestions for:
- Documentation clarity improvements
- Additional validation studies to reference
- Integration examples with other OGC workflows
- Multi-sensor fusion approaches (LiDAR, InSAR, etc.)

### Code Contributions

For significant changes:
1. Open an issue first to discuss the proposed changes
2. Fork the repository
3. Create a feature branch
4. Submit a pull request with clear description of changes

### Scientific Validation

If you have:
- Field data for validation in new regions
- Alternative allometric equations for different mangrove species
- Improvements to detection thresholds

Please open an issue with references to peer-reviewed sources.

## Development Priorities

Current focus areas (in order):
1. Resolve stackstac data loading (coordinate system handling)
2. Integration with coastal vulnerability OSPD workflows
3. Multi-sensor consilience validation (GEDI, Sentinel-1)
4. Historical time series analysis (Landsat archive)

## Contact

For questions about:
- **Scientific methods**: See VALIDATION_COMPARISON.md for references
- **OGC OSPD integration**: Contact via OGC GitLab wiki
- **General inquiries**: Open a GitHub issue

Cameron Sajedi, Starling Foundries
Part of OGC 2025 Open Science Platform Demonstrator series

## Code of Conduct

Be respectful, constructive, and focused on improving open science for conservation applications. This is a demonstration project for ecosystem monitoring - keep discussions relevant to that goal.