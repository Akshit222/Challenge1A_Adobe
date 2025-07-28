FROM --platform=linux/amd64 python:3.10

WORKDIR /app

# Install required libraries
RUN pip install --no-cache-dir PyMuPDF

# Copy the processing script
COPY process_pdfs.py .

# Run the script
CMD ["python", "process_pdfs.py"]
