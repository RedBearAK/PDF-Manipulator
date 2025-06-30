#!/bin/bash

# version = "20250701"

# PDF Manipulator - Bash script using qpdf/pdftk/gs
# Requires: qpdf (recommended) or pdftk, and optionally gs for optimization

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPLACE_ORIGINAL=false
OPTIMIZE=true
AUTO_MODE=false
PDF_TOOL=""

# Function to check available tools
check_tools() {
    if command -v qpdf &> /dev/null; then
        PDF_TOOL="qpdf"
        echo -e "${GREEN}Using qpdf for PDF manipulation${NC}"
    elif command -v pdftk &> /dev/null; then
        PDF_TOOL="pdftk"
        echo -e "${YELLOW}Using pdftk (qpdf recommended for better optimization)${NC}"
    else
        echo -e "${RED}Error: Neither qpdf nor pdftk found!${NC}"
        echo "Please install one of them:"
        echo "  macOS:    brew install qpdf"
        echo "  Ubuntu:   sudo apt-get install qpdf"
        echo "  Fedora:   sudo dnf install qpdf"
        exit 1
    fi
    
    if command -v gs &> /dev/null; then
        echo -e "${GREEN}Ghostscript found for additional optimization${NC}"
    else
        echo -e "${YELLOW}Ghostscript not found - optimization will be limited${NC}"
    fi
}

# Function to get PDF page count
get_page_count() {
    local pdf_file="$1"
    
    if [[ "$PDF_TOOL" == "qpdf" ]]; then
        qpdf --show-npages "$pdf_file" 2>/dev/null || echo "0"
    else
        pdftk "$pdf_file" dump_data 2>/dev/null | grep "NumberOfPages" | awk '{print $2}' || echo "0"
    fi
}

# Function to get file size in MB
get_file_size_mb() {
    local file="$1"
    local size_bytes
    
    if [[ "$OSTYPE" == "darwin"* ]]; then
        size_bytes=$(stat -f%z "$file")
    else
        size_bytes=$(stat -c%s "$file")
    fi
    
    echo "scale=2; $size_bytes / 1024 / 1024" | bc
}

# Function to strip PDF to first page
strip_to_first_page() {
    local input_pdf="$1"
    local output_pdf="${input_pdf%.pdf}_page1.pdf"
    
    if [[ "$PDF_TOOL" == "qpdf" ]]; then
        qpdf --empty --pages "$input_pdf" 1 -- "$output_pdf"
    else
        pdftk "$input_pdf" cat 1 output "$output_pdf"
    fi
    
    echo "$output_pdf"
}

# Function to optimize PDF with qpdf
optimize_with_qpdf() {
    local input_pdf="$1"
    local output_pdf="${input_pdf%.pdf}_optimized.pdf"
    
    qpdf --optimize-images \
         --compress-streams=y \
         --object-streams=generate \
         --linearize \
         "$input_pdf" "$output_pdf"
    
    echo "$output_pdf"
}

# Function to optimize PDF with Ghostscript
optimize_with_gs() {
    local input_pdf="$1"
    local output_pdf="${input_pdf%.pdf}_optimized.pdf"
    
    gs -sDEVICE=pdfwrite \
       -dCompatibilityLevel=1.4 \
       -dPDFSETTINGS=/ebook \
       -dNOPAUSE -dQUIET -dBATCH \
       -sOutputFile="$output_pdf" \
       "$input_pdf"
    
    echo "$output_pdf"
}

# Function to display PDF information
display_pdf_info() {
    local folder="$1"
    
    echo -e "\n${BLUE}PDF Files Assessment${NC}"
    echo "================================================="
    printf "%-40s %8s %12s %s\n" "File" "Pages" "Size (MB)" "Status"
    echo "================================================="
    
    local total_files=0
    local multi_page_files=0
    
    for pdf in "$folder"/*.pdf; do
        [[ -f "$pdf" ]] || continue
        
        local basename
        basename=$(basename "$pdf")
        local page_count
        page_count=$(get_page_count "$pdf")
        local file_size
        file_size=$(get_file_size_mb "$pdf")
        local status
        
        if [[ $page_count -gt 1 ]]; then
            status="${YELLOW}⚠️  Multi-page${NC}"
            ((multi_page_files++))
        else
            status="${GREEN}✓ Single page${NC}"
        fi
        
        printf "%-40s %8s %12s %b\n" "$basename" "$page_count" "$file_size" "$status"
        ((total_files++))
    done
    
    echo "================================================="
    echo -e "Total: $total_files files, $multi_page_files with multiple pages\n"
}

# Function to process a single PDF
process_pdf() {
    local pdf_file="$1"
    local page_count="$2"
    local file_size="$3"
    
    echo -e "\n${CYAN}$(basename "$pdf_file")${NC} - $page_count pages, $file_size MB"
    
    if [[ "$AUTO_MODE" == "true" ]] || confirm "Strip to first page only?"; then
        local output_pdf
        output_pdf=$(strip_to_first_page "$pdf_file")
        
        if [[ -f "$output_pdf" ]]; then
            local new_size
            new_size=$(get_file_size_mb "$output_pdf")
            echo -e "${GREEN}✓ Created:${NC} $(basename "$output_pdf") ($new_size MB)"
            
            # Optimize if requested and tools available
            if [[ "$OPTIMIZE" == "true" ]]; then
                local optimized_pdf=""
                
                if [[ "$PDF_TOOL" == "qpdf" ]]; then
                    optimized_pdf=$(optimize_with_qpdf "$output_pdf")
                elif command -v gs &> /dev/null; then
                    optimized_pdf=$(optimize_with_gs "$output_pdf")
                fi
                
                if [[ -f "$optimized_pdf" ]]; then
                    mv "$optimized_pdf" "$output_pdf"
                    new_size=$(get_file_size_mb "$output_pdf")
                    echo -e "${GREEN}✓ Optimized:${NC} Final size $new_size MB"
                fi
            fi
            
            # Calculate size reduction
            local reduction
            reduction=$(echo "scale=1; ($file_size - $new_size) / $file_size * 100" | bc)
            echo -e "${BLUE}Size reduction: ${reduction}%${NC}"
            
            # Replace original if requested
            if [[ "$REPLACE_ORIGINAL" == "true" ]]; then
                if [[ "$AUTO_MODE" == "true" ]] || confirm "Replace original file?"; then
                    mv "$output_pdf" "$pdf_file"
                    echo -e "${GREEN}✓ Original file replaced${NC}"
                fi
            fi
        fi
    fi
}

# Function to confirm action
confirm() {
    local prompt="$1"
    local response
    
    read -p "$prompt [y/N] " -n 1 -r response
    echo
    [[ $response =~ ^[Yy]$ ]]
}

# Function to show usage
usage() {
    cat << EOF
PDF Manipulator - Assess and manipulate PDF pages

Usage: $(basename "$0") [OPTIONS] [FOLDER]

Options:
    -r, --replace       Replace original files (with confirmation)
    -n, --no-optimize   Skip optimization step
    -a, --auto          Automatically process all multi-page PDFs
    -h, --help          Show this help message

Examples:
    $(basename "$0") .                    # Scan current directory
    $(basename "$0") /path/to/pdfs        # Scan specific directory
    $(basename "$0") -r .                 # Replace originals after confirmation
    $(basename "$0") -a -r .              # Auto-process and replace

Requirements:
    - qpdf (recommended) or pdftk
    - ghostscript (optional, for better optimization)

EOF
}

# Main function
main() {
    local folder="."
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -r|--replace)
                REPLACE_ORIGINAL=true
                shift
                ;;
            -n|--no-optimize)
                OPTIMIZE=false
                shift
                ;;
            -a|--auto)
                AUTO_MODE=true
                shift
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            -*)
                echo -e "${RED}Unknown option: $1${NC}"
                usage
                exit 1
                ;;
            *)
                folder="$1"
                shift
                ;;
        esac
    done
    
    # Check if folder exists
    if [[ ! -d "$folder" ]]; then
        echo -e "${RED}Error: $folder is not a valid directory${NC}"
        exit 1
    fi
    
    # Check for required tools
    check_tools
    echo
    
    # Display PDF information
    echo -e "${BLUE}Scanning $(realpath "$folder")...${NC}"
    display_pdf_info "$folder"
    
    # Process multi-page PDFs
    local processed=0
    for pdf in "$folder"/*.pdf; do
        [[ -f "$pdf" ]] || continue
        
        local page_count
        page_count=$(get_page_count "$pdf")
        if [[ $page_count -gt 1 ]]; then
            local file_size
            file_size=$(get_file_size_mb "$pdf")
            process_pdf "$pdf" "$page_count" "$file_size"
            ((processed++))
        fi
    done
    
    if [[ $processed -eq 0 ]]; then
        echo -e "${GREEN}No multi-page PDFs found!${NC}"
    else
        echo -e "\n${GREEN}Processed $processed multi-page PDFs${NC}"
    fi
}

# Run main function
main "$@"
