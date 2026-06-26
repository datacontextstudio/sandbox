import subprocess, sys, pathlib

subprocess.check_call([sys.executable, "-m", "pip", "install", "fpdf2", "--no-cache-dir", "-q"])

import fpdf
pdf = fpdf.FPDF()
pdf.add_page()
pdf.set_font("Helvetica", size=12)
pdf.cell(0, 10, "warmup")
pdf.output("/tmp/warmup.pdf")

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

# Disable OCR for warmup — we only need to trigger layout/table model downloads.
# Tesseract (installed system-wide) handles OCR at runtime via parser.py config.
pipeline_options = PdfPipelineOptions(do_ocr=False)
DocumentConverter(
    format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
).convert("/tmp/warmup.pdf")
print("PDF pipeline models downloaded")

subprocess.check_call([sys.executable, "-m", "pip", "uninstall", "-y", "fpdf2"])
pathlib.Path("/tmp/warmup.pdf").unlink()
