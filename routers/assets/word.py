import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(log_name="word", log_level=os.getenv("LOG_LEVEL"), log_dir=os.getenv("LOG_PATH"), log_format="default", runtime=True)

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import tempfile
from PIL import Image
import io
import base64
import traceback
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
import asyncio
import psutil
import math
import time

router = APIRouter()

# Global semaphore to control total concurrent Word processing
MAX_CONCURRENT_PROCESSING = 4  # Adjust based on server capacity
processing_semaphore = asyncio.Semaphore(MAX_CONCURRENT_PROCESSING)

def calculate_optimal_workers():
    """Calculate optimal number of worker threads based on system resources."""
    cpu_count = os.cpu_count() or 4
    available_memory = psutil.virtual_memory().available
    memory_per_worker = 500 * 1024 * 1024  # 500MB per worker estimate
    
    # Calculate workers based on CPU and memory constraints
    cpu_based_workers = max(1, cpu_count - 1)  # Leave one core free
    memory_based_workers = max(1, int(available_memory / memory_per_worker))
    
    # Take the minimum of CPU and memory-based calculations
    optimal_workers = min(cpu_based_workers, memory_based_workers)
    
    # Cap at a reasonable maximum
    final_workers = min(optimal_workers, 8)  # Maximum 8 workers per process

    logger.info("Resource utilization:", {
        "total_cpus": cpu_count,
        "available_memory_gb": available_memory / (1024**3),
        "cpu_based_workers": cpu_based_workers,
        "memory_based_workers": memory_based_workers,
        "final_workers": final_workers
    })
    
    return final_workers

def process_page(temp_dir: str, pdf_path: str, page_info: tuple, timeout: int = 30) -> dict:
    """
    Worker function to process a single page and enforce 16:9 aspect ratio.
    Args:
        temp_dir: Path to temporary directory
        pdf_path: Path to PDF file
        page_info: Tuple of (index, page_number)
        timeout: Maximum time in seconds to process a single page
    Returns:
        dict: Processed page information
    """
    i, page_idx = page_info
    page_num = page_idx + 1  # PDF pages are 1-indexed
    output_prefix = str(Path(temp_dir) / f"page_{page_num}")

    try:
        # Convert PDF page to PNG with timeout
        process = subprocess.Popen(
            [
                'pdftoppm',
                '-png',
                '-singlefile',
                '-f',
                str(page_num),
                '-l',
                str(page_num),
                '-r',
                '600',  # High resolution for better quality
                pdf_path,
                output_prefix,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            raise TimeoutError(f"Page {page_num} processing timed out after {timeout} seconds")

        if process.returncode != 0:
            raise Exception(f"pdftoppm failed for page {page_num}: {stderr.decode()}")

        output_file = f"{output_prefix}.png"
        if not Path(output_file).exists():
            raise Exception(f"Could not find output file for page {page_num}")

        # Open and process the image
        with Image.open(output_file) as img:
            return _process_image(img, i)
    except Exception as e:
        logger.error(f"Error processing page {page_num}: {str(e)}")
        return {
            "index": i,
            "error": str(e),
            "success": False,
        }

def _process_image(img: Image.Image, index: int) -> dict:
    """Process a single image, maintaining A4 proportions."""
    try:
        # Determine orientation and target dimensions
        is_portrait = img.height > img.width
        target_height = 720  # Fixed height to match frontend slide height
        
        if is_portrait:
            # A4 portrait ratio is 210:297
            target_width = int(target_height * (210/297))
        else:
            # A4 landscape ratio is 297:210
            target_width = int(target_height * (297/210))

        # Resize image maintaining aspect ratio
        img = img.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # Convert to base64
        buffered = io.BytesIO()
        img.save(buffered, format="PNG", optimize=True)
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return {
            "index": index,
            "data": f"data:image/png;base64,{img_str}",
            "success": True,
            "dimensions": {
                "width": target_width,
                "height": target_height,
                "orientation": "portrait" if is_portrait else "landscape"
            }
        }
    except Exception as e:
        logger.error(f"Error processing image for page {index}: {str(e)}")
        return {
            "index": index,
            "error": str(e),
            "success": False,
        }

async def process_pages_in_chunks(temp_dir: str, pdf_path: str, visible_pages: list, chunk_size: int = 5):
    """Process pages in chunks to manage memory better."""
    all_processed_pages = []
    num_workers = calculate_optimal_workers()
    total_chunks = math.ceil(len(visible_pages) / chunk_size)
    
    logger.info("Starting page processing:", {
        "total_pages": len(visible_pages),
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "workers_per_chunk": num_workers
    })

    # Process pages in chunks
    for chunk_index in range(0, len(visible_pages), chunk_size):
        chunk = visible_pages[chunk_index:chunk_index + chunk_size]
        processed_chunk = []
        current_chunk_num = (chunk_index // chunk_size) + 1

        logger.info(f"Processing chunk {current_chunk_num}/{total_chunks}", {
            "chunk_size": len(chunk),
            "chunk_start_index": chunk_index,
            "memory_usage_gb": psutil.Process().memory_info().rss / (1024**3)
        })

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            # Submit chunk of tasks
            future_to_page = {
                executor.submit(
                    process_page, temp_dir, pdf_path, page_info
                ): page_info
                for page_info in chunk
            }

            # Process completed tasks as they finish
            for future in as_completed(future_to_page):
                try:
                    result = future.result(timeout=60)  # Increased timeout to 60 seconds per page
                    if result.get('success', False):
                        processed_chunk.append(result)
                    page_info = future_to_page[future]
                    logger.debug(f"Processed page {page_info[1] + 1}", {
                        "success": result.get('success', False),
                        "processing_time": time.time() - start_time
                    })
                except TimeoutError:
                    page_info = future_to_page[future]
                    logger.error(f"Timeout processing page {page_info[1] + 1}")
                except Exception as e:
                    page_info = future_to_page[future]
                    logger.error(f"Error processing page {page_info[1] + 1}: {str(e)}")

        chunk_time = time.time() - start_time
        logger.info(f"Completed chunk {current_chunk_num}/{total_chunks}", {
            "processed_pages": len(processed_chunk),
            "chunk_processing_time": chunk_time,
            "avg_time_per_page": chunk_time / len(chunk) if chunk else 0
        })

        all_processed_pages.extend(processed_chunk)

        # Small delay between chunks to allow other tasks to process
        await asyncio.sleep(0.1)

    return all_processed_pages

@router.post("/convert")
async def convert_docx_to_images(file: UploadFile = File(...)):
    try:
        async with processing_semaphore:  # Control concurrent processing
            start_time = time.time()
            # Log request details
            logger.info(
                "Received file upload request",
                {
                    "filename": file.filename,
                    "content_type": file.content_type,
                    "current_memory_usage_gb": psutil.Process()
                    .memory_info()
                    .rss
                    / (1024**3),
                    "cpu_percent": psutil.cpu_percent(interval=1),
                },
            )

            # Validate file
            if not file.filename.endswith('.docx'):
                logger.error("Invalid file type")
                return JSONResponse({
                    "status": "error",
                    "message": "Invalid file type. Please upload a .docx file"
                }, status_code=400)

            # Create a temporary directory to store the Word file
            with tempfile.TemporaryDirectory() as temp_dir:
                docx_path = Path(temp_dir) / "document.docx"
                pdf_path = Path(temp_dir) / "document.pdf"

                logger.debug(f"Saving file to temporary path: {docx_path}")

                try:
                    # Save uploaded file
                    content = await file.read()
                    logger.debug(f"Read file content, size: {len(content)} bytes")

                    with open(docx_path, "wb") as buffer:
                        buffer.write(content)
                    logger.debug("File saved successfully")

                    if not docx_path.exists() or docx_path.stat().st_size == 0:
                        raise Exception("Failed to save file or file is empty")

                    # Convert Word to PDF using LibreOffice
                    logger.debug("Converting Word to PDF")
                    result = subprocess.run([
                        'soffice',
                        '--headless',
                        '--convert-to', 'pdf',
                        '--outdir', str(temp_dir),
                        str(docx_path)
                    ], check=True, capture_output=True, text=True)

                    if not pdf_path.exists():
                        raise Exception("PDF file was not created")

                    logger.debug(f"PDF created successfully at {pdf_path}, size: {pdf_path.stat().st_size} bytes")

                    # Get number of pages using pdfinfo
                    result = subprocess.run(['pdfinfo', str(pdf_path)], capture_output=True, text=True)
                    pages_line = [line for line in result.stdout.split('\n') if line.startswith('Pages:')][0]
                    num_pages = int(pages_line.split(':')[1].strip())

                    visible_pages = [(i, i) for i in range(num_pages)]

                    if num_pages == 0:
                        logger.warning("No pages found in document")
                        return JSONResponse({
                            "status": "error",
                            "message": "No pages found in document"
                        }, status_code=400)

                    logger.info(f"Processing {num_pages} pages")

                    # Calculate chunk size based on number of pages
                    chunk_size = min(5, max(2, math.ceil(num_pages / 4)))
                    processed_pages = await process_pages_in_chunks(str(temp_dir), str(pdf_path), visible_pages, chunk_size)

                    if not processed_pages:
                        raise Exception("Failed to process any pages successfully")

                    # Sort pages by index
                    processed_pages.sort(key=lambda x: x['index'])

                    logger.info(f"Successfully processed {len(processed_pages)} pages")

                    # After processing all pages
                    total_time = time.time() - start_time
                    logger.info("Word document processing completed", {
                        "total_processing_time": total_time,
                        "pages_processed": len(processed_pages),
                        "avg_time_per_page": total_time / len(processed_pages) if processed_pages else 0,
                        "final_memory_usage_gb": psutil.Process().memory_info().rss / (1024**3)
                    })

                    return JSONResponse({
                        "status": "success",
                        "slides": processed_pages,  # Using same format as PowerPoint for consistency
                        "processing_stats": {
                            "total_time": total_time,
                            "pages_processed": len(processed_pages),
                            "avg_time_per_page": total_time / len(processed_pages) if processed_pages else 0
                        }
                    })

                except Exception as inner_error:
                    logger.error(f"Inner error: {str(inner_error)}")
                    logger.error(traceback.format_exc())
                    raise

    except Exception as e:
        logger.error(f"Error processing Word document: {str(e)}")
        logger.error(f"Python version: {sys.version}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse({
            "status": "error",
            "message": f"Failed to process Word document: {str(e)}"
        }, status_code=500)
