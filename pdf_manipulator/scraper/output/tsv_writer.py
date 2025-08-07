"""
TSV output writer for extracted data.
"""

import csv
from pathlib import Path


class TSVWriter:
    """
    Write extraction results to tab-separated values (TSV) format.
    
    TSV is preferred over CSV for data that might contain commas,
    making it more reliable for spreadsheet import.
    """
    
    def __init__(self):
        pass
    
    def write_results(self, output_path, headers, rows):
        """
        Write extraction results to a TSV file.
        
        Args:
            output_path (str): Path for the output file
            headers (list): Column headers
            rows (list): List of data rows, each row is a list of values
            
        Raises:
            IOError: If file cannot be written
        """
        output_path = Path(output_path)
        
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
                
                # Write headers
                writer.writerow(headers)
                
                # Write data rows
                for row in rows:
                    # Clean and format each cell
                    cleaned_row = [self._clean_cell_value(cell) for cell in row]
                    writer.writerow(cleaned_row)
                    
        except IOError as e:
            raise IOError(f"Cannot write to {output_path}: {e}")
    
    def append_results(self, output_path, rows):
        """
        Append results to an existing TSV file.
        
        Args:
            output_path (str): Path to existing TSV file
            rows (list): List of data rows to append
            
        Raises:
            IOError: If file cannot be written
            FileNotFoundError: If file doesn't exist for appending
        """
        output_path = Path(output_path)
        
        if not output_path.exists():
            raise FileNotFoundError(f"Cannot append to non-existent file: {output_path}")
        
        try:
            with open(output_path, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file, delimiter='\t', quoting=csv.QUOTE_MINIMAL)
                
                for row in rows:
                    cleaned_row = [self._clean_cell_value(cell) for cell in row]
                    writer.writerow(cleaned_row)
                    
        except IOError as e:
            raise IOError(f"Cannot append to {output_path}: {e}")
    
    def _clean_cell_value(self, value):
        """
        Clean a cell value for TSV output.
        
        Args:
            value: Raw cell value
            
        Returns:
            str: Cleaned value suitable for TSV
        """
        if value is None:
            return ''
        
        # Convert to string
        str_value = str(value)
        
        # Replace problematic characters
        # Remove or replace tabs and newlines that would break TSV format
        str_value = str_value.replace('\t', ' ').replace('\n', ' ').replace('\r', '')
        
        # Normalize whitespace
        str_value = ' '.join(str_value.split())
        
        # Handle special cases for numeric data
        if self._looks_like_number(str_value):
            # Remove spaces from numbers for better spreadsheet compatibility
            str_value = str_value.replace(' ', '')
        
        return str_value
    
    def _looks_like_number(self, value):
        """Check if a string looks like a number."""
        if not value:
            return False
        
        # Remove common number formatting characters
        test_value = value.replace(',', '').replace(' ', '').replace('$', '')
        
        try:
            float(test_value)
            return True
        except ValueError:
            return False
    
    def validate_data(self, headers, rows):
        """
        Validate data before writing.
        
        Args:
            headers (list): Column headers
            rows (list): Data rows
            
        Returns:
            dict: Validation results with 'valid' (bool) and 'errors' (list)
        """
        errors = []
        
        if not headers:
            errors.append("Headers cannot be empty")
        
        if not rows:
            errors.append("No data rows provided")
            return {'valid': False, 'errors': errors}
        
        expected_columns = len(headers)
        
        for i, row in enumerate(rows):
            if len(row) != expected_columns:
                errors.append(f"Row {i+1}: Expected {expected_columns} columns, got {len(row)}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def preview_output(self, headers, rows, max_rows=5):
        """
        Generate a preview of what the TSV output will look like.
        
        Args:
            headers (list): Column headers
            rows (list): Data rows
            max_rows (int): Maximum number of rows to preview
            
        Returns:
            str: Preview of TSV content
        """
        preview_lines = []
        
        # Add headers
        header_line = '\t'.join(str(h) for h in headers)
        preview_lines.append(header_line)
        
        # Add data rows (limited)
        for i, row in enumerate(rows[:max_rows]):
            cleaned_row = [self._clean_cell_value(cell) for cell in row]
            row_line = '\t'.join(cleaned_row)
            preview_lines.append(row_line)
        
        if len(rows) > max_rows:
            preview_lines.append(f"... ({len(rows) - max_rows} more rows)")
        
        return '\n'.join(preview_lines)
    
    def get_stats(self, headers, rows):
        """
        Get statistics about the data to be written.
        
        Returns:
            dict: Statistics including row count, column count, etc.
        """
        if not rows:
            return {
                'total_rows': 0,
                'total_columns': len(headers) if headers else 0,
                'empty_cells': 0,
                'non_empty_cells': 0
            }
        
        total_cells = len(rows) * len(headers)
        empty_cells = 0
        
        for row in rows:
            for cell in row:
                if not cell or str(cell).strip() == '':
                    empty_cells += 1
        
        return {
            'total_rows': len(rows),
            'total_columns': len(headers),
            'total_cells': total_cells,
            'empty_cells': empty_cells,
            'non_empty_cells': total_cells - empty_cells,
            'fill_rate': (total_cells - empty_cells) / total_cells if total_cells > 0 else 0
        }
