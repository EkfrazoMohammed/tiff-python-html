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
@app.post("/convert-tiff")
async def convert_tiff(file: UploadFile = File(...)):
    try:
        # Read the uploaded file
        contents = await file.read()

        # Open the TIFF file from the uploaded bytes
        with rasterio.open(io.BytesIO(contents)) as src:
            # Transform bounds to WGS84 if necessary
            bounds = transform_bounds(src.crs, "EPSG:4326", *src.bounds) if src.crs != "EPSG:4326" else src.bounds
            # Read and process the image data
            data = src.read(out_shape=(src.count, src.height // 10, src.width // 10))
            data = reshape_as_image(data[:3])  # RGB bands
            data_normalized = ((data - data.min()) / (data.max() - data.min()) * 255).astype(np.uint8)
            
            # Create a PNG image from the processed array
            img = Image.fromarray(data_normalized)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')

            # Convert image to base64 string
            img_byte_arr.seek(0)  # Reset pointer to the beginning of the image byte array
            img_base64 = base64.b64encode(img_byte_arr.read()).decode('utf-8')

            # Return the base64 image and bounds in JSON response
            return JSONResponse(content={'base64_image': f"data:image/png;base64,{img_base64}", 'bounds': [
                [bounds[1], bounds[0]],  # [min_lat, min_lon]
                [bounds[3], bounds[2]]   # [max_lat, max_lon]
            ]})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.post("/get-bounds")
async def get_bounds(file: UploadFile = File(...)):
    try:
        # Read the uploaded file contents
        contents = await file.read()

        # Open the TIFF file from the uploaded bytes
        with rasterio.open(io.BytesIO(contents)) as src:
            # Extract the bounds (min_lon, min_lat, max_lon, max_lat)
            bounds = src.bounds
            crs = src.crs

            # Convert bounds to WGS84 (EPSG:4326) if necessary
            if crs != 'EPSG:4326':
                bounds = transform_bounds(crs, 'EPSG:4326', *bounds)

            # Return the bounds in a JSON response
            return JSONResponse(content={'bounds': [
                [bounds[0], bounds[1]],  # [min_lon, min_lat]
                [bounds[2], bounds[3]]   # [max_lon, max_lat]
            ]})
    
    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.post("/convert-gpkg")
async def convert_gpkg(file: UploadFile = File(...)):
    try:
        # Read the uploaded file
        contents = await file.read()
        gpkg = io.BytesIO(contents)

        # Use geopandas to read the GeoPackage file
        gdf = gpd.read_file(gpkg)

        # Convert GeoDataFrame to GeoJSON for use in the frontend
        geojson = gdf.to_json()

        return JSONResponse(content={'geojson': geojson})

    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})


@app.post("/convert-shp")
async def convert_shp(file: UploadFile = File(...)):
    try:
        # Read the uploaded file
        contents = await file.read()
        shp = io.BytesIO(contents)

        # Use geopandas to read the shapefile
        gdf = gpd.read_file(shp)

        # Convert GeoDataFrame to GeoJSON for use in the frontend
        geojson = gdf.to_json()

        return JSONResponse(content={'geojson': geojson})

    except Exception as e:
        return JSONResponse(status_code=500, content={'error': str(e)})

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
