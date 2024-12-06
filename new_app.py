from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import geopandas as gpd
from PIL import Image
import rasterio
import numpy as np
import io
import base64
from rasterio.plot import reshape_as_image
from rasterio.warp import transform_bounds

app = FastAPI()
origins = [
    "http://127.0.0.1:5500",  # Allow your local HTML to make requests
    "*",  # Or allow all origins (for development purposes only)
]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows specific origins or "*" for any origin
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)
@app.post("/convert-tiff/")
async def convert_tiff(file: UploadFile = File(...)):
    try:
        # Read the uploaded file
        contents = await file.read()

        # Open the TIFF file from the uploaded bytes
        with rasterio.open(io.BytesIO(contents)) as src:
            # Transform bounds to WGS84 if necessary
            bounds = (
                transform_bounds(src.crs, "EPSG:4326", *src.bounds)
                if src.crs != "EPSG:4326"
                else src.bounds
            )

            # Read the image data
            data = src.read()

            # Handle floating-point data: normalize to uint8
            if np.issubdtype(data.dtype, np.floating):
                data = np.nan_to_num(data)  # Replace NaN with 0
                data = (
                    (data - data.min())
                    / (data.max() - data.min())
                    * 255
                ).astype(np.uint8)

            # If the TIFF has more than 3 bands, limit to the first three (RGB)
            if data.shape[0] > 3:
                data = data[:3]

            # Convert the normalized array to an RGB image
            img = Image.fromarray(reshape_as_image(data))

            # Add an alpha channel for transparency
            img = img.convert("RGBA")

            # Replace black pixels with transparent ones (customizable threshold)
            datas = img.getdata()
            new_data = [
                (0, 0, 0, 0) if max(item[:3]) < 10 else item for item in datas
            ]
            img.putdata(new_data)

            # Save the image to a byte array with high-quality compression
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="PNG", optimize=True)

            # Convert image to base64 string
            img_byte_arr.seek(0)
            img_base64 = base64.b64encode(img_byte_arr.read()).decode("utf-8")

            # Return the base64 image and bounds in JSON response
            return JSONResponse(
                content={
                    "base64_image": f"data:image/png;base64,{img_base64}",
                    "bounds": [
                        [bounds[1], bounds[0]],  # [min_lat, min_lon]
                        [bounds[3], bounds[2]],  # [max_lat, max_lon]
                    ],
                }
            )

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/convert-tiff-old/")
async def convert_tiff(file: UploadFile = File(...)):
    try:
        # Read the uploaded file
        contents = await file.read()

        # Open the TIFF file from the uploaded bytes
        with rasterio.open(io.BytesIO(contents)) as src:
            # Transform bounds to WGS84 if necessary
            bounds = (
                transform_bounds(src.crs, "EPSG:4326", *src.bounds)
                if src.crs != "EPSG:4326"
                else src.bounds
            )
            # Read and process the image data
            data = src.read(out_shape=(src.count, src.height // 10, src.width // 10))
            data = reshape_as_image(data[:3])  # RGB bands
            data_normalized = (
                (data - data.min()) / (data.max() - data.min()) * 255
            ).astype(np.uint8)

            # Convert to RGBA (adding alpha channel)
            img = Image.fromarray(data_normalized)
            img = img.convert("RGBA")

            # Replace black pixels with transparent ones
            datas = img.getdata()
            new_data = []
            for item in datas:
                # Change all black (also shades of black)
                if item[0] < 10 and item[1] < 10 and item[2] < 10:
                    new_data.append((0, 0, 0, 0))  # Set transparency (alpha = 0)
                else:
                    new_data.append(item)
            img.putdata(new_data)

            # Save the image to a byte array
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="PNG")

            # Convert image to base64 string
            img_byte_arr.seek(
                0
            )  # Reset pointer to the beginning of the image byte array
            img_base64 = base64.b64encode(img_byte_arr.read()).decode("utf-8")

            # Return the base64 image and bounds in JSON response
            return JSONResponse(
                content={
                    "base64_image": f"data:image/png;base64,{img_base64}",
                    "bounds": [
                        [bounds[1], bounds[0]],  # [min_lat, min_lon]
                        [bounds[3], bounds[2]],  # [max_lat, max_lon]
                    ],
                }
            )

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# @app.post("/convert-tiff-hd/")
# async def convert_tiff(file: UploadFile = File(...)):
#     try:
#         # Read the uploaded file
#         contents = await file.read()

#         # Open the TIFF file from the uploaded bytes
#         with rasterio.open(io.BytesIO(contents)) as src:
#             # Transform bounds to WGS84 if necessary
#             bounds = (
#                 transform_bounds(src.crs, "EPSG:4326", *src.bounds)
#                 if src.crs != "EPSG:4326"
#                 else src.bounds
#             )
            
#             # Read the image data without downscaling
#             data = src.read()
            
#             # If the TIFF has more than 3 bands, limit to the first three (RGB)
#             if data.shape[0] > 3:
#                 data = data[:3]

#             # Normalize the data to 8-bit
#             data = np.nan_to_num(data)  # Replace NaNs with 0
#             data_normalized = (
#                 (data - data.min()) / (data.max() - data.min()) * 255
#             ).astype(np.uint8)

#             # Convert the normalized array to an RGB image
#             img = Image.fromarray(reshape_as_image(data_normalized))

#             # Add an alpha channel for transparency
#             img = img.convert("RGBA")

#             # Replace black pixels with transparent ones
#             datas = img.getdata()
#             new_data = [
#                 (0, 0, 0, 0) if item[:3] == (0, 0, 0) else item for item in datas
#             ]
#             img.putdata(new_data)

#             # Save the image to a byte array with high-quality compression
#             img_byte_arr = io.BytesIO()
#             img.save(img_byte_arr, format="PNG", optimize=True)

#             # Convert image to base64 string
#             img_byte_arr.seek(0)
#             img_base64 = base64.b64encode(img_byte_arr.read()).decode("utf-8")

#             # Return the base64 image and bounds in JSON response
#             return JSONResponse(
#                 content={
#                     "base64_image": f"data:image/png;base64,{img_base64}",
#                     "bounds": [
#                         [bounds[1], bounds[0]],  # [min_lat, min_lon]
#                         [bounds[3], bounds[2]],  # [max_lat, max_lon]
#                     ],
#                 }
#             )

#     except Exception as e:
#         return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8005)
