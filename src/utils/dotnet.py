def version_build_id(version: str) -> str:
    # Extract suffix from the version
    suffix = version.split('-')[-1]
    
    # Check if the suffix is the same as the version
    if suffix == version:
        # Dummy BuildID used when official BuildID is unknown.
        return "20200101.1"
    else:
        # Extract the revision, suffix, and short date from the suffix
        revision = suffix.split('.')[-1]
        suffix = '.'.join(suffix.split('.')[:-1])
        short_date = suffix.split('.')[-1]
        
        # Calculate year, month, and day from short_date
        yy = int(short_date) // 1000
        mm = (int(short_date) - 1000 * yy) // 50
        dd = int(short_date) - 1000 * yy - 50 * mm
        
        # Format the build ID
        build_id = f"20{yy:02d}{mm:02d}{dd:02d}.{revision}"
        return build_id
