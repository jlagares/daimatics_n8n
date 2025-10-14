#!/usr/bin/env python3
"""
deduplicate.py - Remove duplicates from CSV files based on URL column

This script uses pandas to:
1. Read a CSV file from a specified folder
2. Remove duplicate rows based on the 'url' column
3. Save the cleaned data back to a new file or overwrite the original

Usage:
    python deduplicate.py <input_file> [--output <output_file>] [--column <column_name>]
    
Examples:
    python deduplicate.py data/emails.csv
    python deduplicate.py data/emails.csv --output data/emails_clean.csv
    python deduplicate.py data/emails.csv --column source --output data/cleaned.csv
"""

import argparse
import pandas as pd
import os
import sys
from pathlib import Path

def remove_duplicates(input_file, output_file=None, column='url', keep='first'):
    """
    Remove duplicates from CSV file based on specified column
    
    Args:
        input_file (str): Path to input CSV file
        output_file (str): Path to output CSV file (optional)
        column (str): Column name to check for duplicates (default: 'url')
        keep (str): Which duplicate to keep ('first', 'last', or False to drop all)
    
    Returns:
        dict: Statistics about the deduplication process
    """
    
    # Check if input file exists
    if not os.path.exists(input_file):
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    print(f"Reading CSV file: {input_file}")
    
    try:
        # Read the CSV file
        df = pd.read_csv(input_file)
        original_count = len(df)
        
        print(f"Original number of rows: {original_count}")
        print(f"Columns found: {list(df.columns)}")
        
        # Check if the specified column exists
        if column not in df.columns:
            available_columns = list(df.columns)
            raise ValueError(f"Column '{column}' not found. Available columns: {available_columns}")
        
        # Show some statistics before deduplication
        unique_before = df[column].nunique()
        print(f"Unique values in '{column}' column before deduplication: {unique_before}")
        
        # Remove duplicates based on the specified column
        df_clean = df.drop_duplicates(subset=[column], keep=keep)
        clean_count = len(df_clean)
        duplicates_removed = original_count - clean_count
        
        print(f"Rows after deduplication: {clean_count}")
        print(f"Duplicates removed: {duplicates_removed}")
        
        # Determine output file
        if output_file is None:
            # Create output filename by adding '_deduplicated' before the extension
            input_path = Path(input_file)
            output_file = input_path.parent / f"{input_path.stem}_deduplicated{input_path.suffix}"
        
        # Save the cleaned data
        df_clean.to_csv(output_file, index=False)
        print(f"Cleaned data saved to: {output_file}")
        
        # Return statistics
        return {
            'original_count': original_count,
            'clean_count': clean_count,
            'duplicates_removed': duplicates_removed,
            'unique_values': df_clean[column].nunique(),
            'input_file': input_file,
            'output_file': str(output_file)
        }
        
    except pd.errors.EmptyDataError:
        raise ValueError("The input file is empty or contains no data")
    except pd.errors.ParserError as e:
        raise ValueError(f"Error parsing CSV file: {e}")
    except Exception as e:
        raise Exception(f"An error occurred while processing the file: {e}")

def show_duplicate_analysis(input_file, column='url'):
    """
    Show analysis of duplicates without removing them
    
    Args:
        input_file (str): Path to input CSV file
        column (str): Column name to analyze for duplicates
    """
    
    try:
        df = pd.read_csv(input_file)
        
        print(f"\n=== Duplicate Analysis for '{column}' column ===")
        print(f"Total rows: {len(df)}")
        print(f"Unique values: {df[column].nunique()}")
        
        # Find duplicates
        duplicates = df[df.duplicated(subset=[column], keep=False)]
        
        if len(duplicates) > 0:
            print(f"Duplicate rows found: {len(duplicates)}")
            print(f"Unique values that have duplicates: {duplicates[column].nunique()}")
            
            # Show the most common duplicates
            duplicate_counts = duplicates[column].value_counts().head(10)
            print(f"\nTop duplicate values:")
            for value, count in duplicate_counts.items():
                print(f"  {value}: {count} occurrences")
        else:
            print("No duplicates found!")
            
    except Exception as e:
        print(f"Error during analysis: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Remove duplicates from CSV files based on URL column",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deduplicate.py data/emails.csv
  python deduplicate.py data/emails.csv --output data/emails_clean.csv
  python deduplicate.py data/emails.csv --column source
  python deduplicate.py data/emails.csv --analyze-only
        """
    )
    
    parser.add_argument('input_file', help='Path to input CSV file')
    parser.add_argument('--output', '-o', help='Path to output CSV file (optional)')
    parser.add_argument('--column', '-c', default='url', 
                       help='Column name to check for duplicates (default: url)')
    parser.add_argument('--keep', choices=['first', 'last'], default='first',
                       help='Which duplicate to keep (default: first)')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze duplicates without removing them')
    
    args = parser.parse_args()
    
    try:
        if args.analyze_only:
            show_duplicate_analysis(args.input_file, args.column)
        else:
            stats = remove_duplicates(
                input_file=args.input_file,
                output_file=args.output,
                column=args.column,
                keep=args.keep
            )
            
            print(f"\n=== Deduplication Summary ===")
            print(f"Input file: {stats['input_file']}")
            print(f"Output file: {stats['output_file']}")
            print(f"Original rows: {stats['original_count']}")
            print(f"Clean rows: {stats['clean_count']}")
            print(f"Duplicates removed: {stats['duplicates_removed']}")
            print(f"Unique {args.column} values: {stats['unique_values']}")
            
            if stats['duplicates_removed'] > 0:
                percentage = (stats['duplicates_removed'] / stats['original_count']) * 100
                print(f"Reduction: {percentage:.1f}%")
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()