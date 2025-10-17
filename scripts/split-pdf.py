#!/usr/bin/env python3
"""Split large PDF files into smaller chunks for easier processing."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter


def get_page_count(pdf_path: str) -> int:
    """Get the number of pages in a PDF file."""
    reader = PdfReader(pdf_path)
    return len(reader.pages)


def split_pdf(input_path: str, output_dir: str, pages_per_file: int = 50):
    """Split a PDF into multiple smaller files.

    Args:
        input_path: Path to the input PDF file
        output_dir: Directory to save split files
        pages_per_file: Number of pages per output file
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(input_path)
    total_pages = len(reader.pages)

    print(f"📄 Input PDF: {input_path.name}")
    print(f"📊 Total pages: {total_pages}")
    print(f"✂️  Splitting into files with ~{pages_per_file} pages each\n")

    file_num = 1
    current_writer = PdfWriter()
    pages_in_current_file = 0

    for page_num in range(total_pages):
        current_writer.add_page(reader.pages[page_num])
        pages_in_current_file += 1

        # Save when we reach the desired page count or it's the last page
        if pages_in_current_file == pages_per_file or page_num == total_pages - 1:
            start_page = (file_num - 1) * pages_per_file + 1
            end_page = start_page + pages_in_current_file - 1

            output_name = (
                f"{input_path.stem}_part{file_num:02d}_pages{start_page:03d}-{end_page:03d}.pdf"
            )
            output_path = output_dir / output_name

            with open(output_path, "wb") as output_file:
                current_writer.write(output_file)

            print(f"✅ Created: {output_name} ({pages_in_current_file} pages)")

            # Reset for next file
            file_num += 1
            current_writer = PdfWriter()
            pages_in_current_file = 0

    print(f"\n🎉 Successfully split into {file_num - 1} files in: {output_dir}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Split large PDF files")
    parser.add_argument("input_pdf", help="Path to input PDF file")
    parser.add_argument(
        "--output-dir", default="./docs/sample pdf/split", help="Output directory for split files"
    )
    parser.add_argument(
        "--pages-per-file", type=int, default=50, help="Pages per output file (default: 50)"
    )
    parser.add_argument(
        "--info-only", action="store_true", help="Only show PDF info without splitting"
    )

    args = parser.parse_args()

    if args.info_only:
        page_count = get_page_count(args.input_pdf)
        print(f"📄 {Path(args.input_pdf).name}")
        print(f"📊 Pages: {page_count}")
    else:
        split_pdf(args.input_pdf, args.output_dir, args.pages_per_file)
