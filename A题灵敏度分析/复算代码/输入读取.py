"""Read the original two workbooks; no preprocessing or duplicate data cache."""
import numpy as np

def load_observations(folder):
    """Read the two original workbooks without creating a duplicate input file."""
    from pathlib import Path
    from openpyxl import load_workbook
    arrays = {}
    for filename, width, key in [('附件1.xlsx', 3, 'environment'),
                                 ('附件2.xlsx', 2, 'radius_data')]:
        workbook = load_workbook(Path(folder)/filename, read_only=True, data_only=True)
        try:
            rows = list(workbook.worksheets[0].values)
        finally:
            workbook.close()
        values = np.asarray([row[:width] for row in rows[1:]
                             if any(v is not None for v in row[:width])], float)
        if (values.ndim != 2 or values.shape[1] != width
                or not np.isfinite(values).all() or values[0,0] != 0
                or not np.all(np.diff(values[:,0]) > 0)):
            raise ValueError(f'Invalid original observations: {filename}')
        arrays[key] = values
    return arrays

