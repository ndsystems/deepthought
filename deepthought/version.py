"""Version information."""

__version_info__ = (2, 0, 0, 'alpha', 0)
# Format: (major, minor, patch, release_type, alpha/beta_version)
# release_type can be 'alpha', 'beta', 'rc' or 'final'

def get_version():
    """Get the version string."""
    major, minor, patch, release_type, sub = __version_info__

    version = f"{major}.{minor}.{patch}"
    
    if release_type != 'final':
        # For alpha/beta releases, include both the type and sub-version
        # e.g. 2.0.0-alpha.0, 2.0.0-beta.1, etc.
        version = f"{version}-{release_type}.{sub}"
    
    return version

__version__ = get_version()
