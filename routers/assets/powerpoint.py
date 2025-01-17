import os
from modules.logger_tool import initialise_logger
logger = initialise_logger(log_name="powerpoint", log_level=os.getenv("LOG_LEVEL"), log_dir=os.getenv("LOG_PATH"), log_format="default", runtime=True)

from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pathlib import Path
import tempfile
from pptx import Presentation
from PIL import Image
import io
import base64
import traceback
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

router = APIRouter()

def process_slide(temp_dir: str, pdf_path: str, slide_info: tuple) -> dict:
    """
    Worker function to process a single slide and enforce 16:9 aspect ratio.
    Args:
        temp_dir: Path to temporary directory
        pdf_path: Path to PDF file
        slide_info: Tuple of (index, slide_number)
    Returns:
        dict: Processed slide information
    """
    i, slide_idx = slide_info
    slide_num = slide_idx + 1  # PDF pages are 1-indexed
    output_prefix = str(Path(temp_dir) / f"slide_{slide_num}")

    try:
        # Convert PDF page to PNG
        subprocess.run(
            [
                'pdftoppm',
                '-png',
                '-singlefile',
                '-f',
                str(slide_num),
                '-l',
                str(slide_num),
                '-r',
                '600',  # High resolution for better quality
                pdf_path,
                output_prefix,
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        output_file = f"{output_prefix}.png"
        if not Path(output_file).exists():
            raise Exception(f"Could not find output file for slide {slide_num}")

        # Open and process the image
        with Image.open(output_file) as img:
            # Enforce 16:9 aspect ratio
            target_aspect_ratio = 16 / 9
            img_aspect_ratio = img.width / img.height

            if img_aspect_ratio > target_aspect_ratio:  # Wider than 16:9
                # Crop the sides
                new_width = int(img.height * target_aspect_ratio)
                offset = (img.width - new_width) // 2
                img = img.crop((offset, 0, offset + new_width, img.height))
            elif img_aspect_ratio < target_aspect_ratio:  # Taller than 16:9
                # Crop the top and bottom
                new_height = int(img.width / target_aspect_ratio)
                offset = (img.height - new_height) // 2
                img = img.crop((0, offset, img.width, offset + new_height))

            # Resize to target resolution (2560x1440)
            img = img.resize((2560, 1440), Image.Resampling.LANCZOS)

            # Convert to base64
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()

            return {
                "index": i,
                "data": f"data:image/png;base64,{img_str}",
                "success": True,
            }

    except Exception as e:
        logger.error(f"Error processing slide {slide_num}: {str(e)}")
        return {
            "index": i,
            "error": str(e),
            "success": False,
        }

@router.get("/test")
async def test_route():
    logger.info("Test route accessed")
    print("Test route accessed")  # Direct console output for immediate feedback
    return {"message": "PowerPoint router is working"}

@router.post("/convert")
async def convert_pptx_to_images(file: UploadFile = File(...)):
    try:
        # Log request details
        logger.info(f"Received file upload request - Filename: {file.filename}, Content-Type: {file.content_type}")

        # Validate file
        if not file.filename.endswith('.pptx'):
            logger.error("Invalid file type")
            return JSONResponse({
                "status": "error",
                "message": "Invalid file type. Please upload a .pptx file"
            }, status_code=400)

        # Create a temporary directory to store the PowerPoint file
        with tempfile.TemporaryDirectory() as temp_dir:
            pptx_path = Path(temp_dir) / "presentation.pptx"
            logger.debug(f"Saving file to temporary path: {pptx_path}")

            try:
                # Save uploaded file
                content = await file.read()
                logger.debug(f"Read file content, size: {len(content)} bytes")

                with open(pptx_path, "wb") as buffer:
                    buffer.write(content)
                logger.debug("File saved successfully")

                if not pptx_path.exists() or pptx_path.stat().st_size == 0:
                    raise Exception("Failed to save file or file is empty")

                # Open the presentation and get visible slides
                prs = Presentation(str(pptx_path))
                visible_slides = [
                    (i, slide_idx)
                    for i, (slide_idx, _) in enumerate(
                        (i, slide)
                        for i, slide in enumerate(prs.slides)
                        if not hasattr(slide, 'show') or slide.show
                    )
                ]
                num_slides = len(visible_slides)

                if num_slides == 0:
                    logger.warning("No visible slides found in presentation")
                    return JSONResponse({
                        "status": "error",
                        "message": "No visible slides found in presentation"
                    }, status_code=400)

                logger.info(f"Processing {num_slides} visible slides")

                # Convert PowerPoint to PDF
                pdf_path = Path(temp_dir) / "presentation.pdf"
                logger.debug("Converting PowerPoint to PDF")

                result = subprocess.run([
                    'soffice',
                    '--headless',
                    '--convert-to', 'pdf',
                    '--outdir', str(temp_dir),
                    str(pptx_path)
                ], check=True, capture_output=True, text=True)

                if not pdf_path.exists():
                    raise Exception("PDF file was not created")

                logger.debug(f"PDF created successfully at {pdf_path}, size: {pdf_path.stat().st_size} bytes")

                # Process slides in parallel
                num_workers = min(os.cpu_count() or 4, 4)  # Limit to 4 threads
                logger.info(f"Starting parallel processing with {num_workers} threads")
                
                processed_slides = []
                with ThreadPoolExecutor(max_workers=num_workers) as executor:
                    # Submit all tasks
                    future_to_slide = {
                        executor.submit(process_slide, str(temp_dir), str(pdf_path), slide_info): slide_info
                        for slide_info in visible_slides
                    }
                    
                    # Process completed tasks as they finish
                    for future in as_completed(future_to_slide):
                        try:
                            result = future.result()
                            if result.get('success', False):
                                processed_slides.append(result)
                        except Exception as e:
                            slide_info = future_to_slide[future]
                            logger.error(f"Error processing slide {slide_info[1] + 1}: {str(e)}")
                
                if not processed_slides:
                    raise Exception("Failed to process any slides successfully")
                
                # Sort slides by index
                processed_slides.sort(key=lambda x: x['index'])
                
                logger.info(f"Successfully processed {len(processed_slides)} slides")
                return JSONResponse({
                    "status": "success",
                    "slides": processed_slides
                })

            except Exception as inner_error:
                logger.error(f"Inner error: {str(inner_error)}")
                logger.error(traceback.format_exc())
                raise

    except Exception as e:
        logger.error(f"Error processing PowerPoint: {str(e)}")
        logger.error(f"Python version: {sys.version}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse({
            "status": "error",
            "message": f"Failed to process PowerPoint: {str(e)}"
        }, status_code=500)