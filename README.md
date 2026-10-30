# Cable Point Annotator

A small local desktop tool for marking up to four cable points per image.

## Run

Install Python 3.10 or newer, then run:

```powershell
py -m pip install -r requirements.txt
py app.py
```

Open the folder containing images. Click the image to add points; click near an existing point to remove it. Export each image when finished.

The app always uses `annotations.csv` in the selected image folder. When a folder is opened, its CSV is loaded into memory; selecting an image restores points by matching the `nama` column to its filename. **Buka CSV** shows the CSV contents in an in-app table. **Refresh gambar** rescans the folder and refreshes the open CSV table. Export writes/updates the matching row, overwrites `marked_img/<original filename>`, leaves the source unchanged, and refreshes the CSV table. CSV columns are `nama,x1,y1,x2,y2,x3,y3,x4,y4`. Coordinates are original image pixel coordinates. Point order follows the order points were added. Close the CSV in Excel before exporting so the app can write the updated CSV.
