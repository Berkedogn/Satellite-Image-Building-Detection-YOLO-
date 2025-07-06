import ee

# 1. Authenticate ve Initialize (ilk çalıştırmada Authentication gerektirir)
ee.Authenticate()  
ee.Initialize(project='psychic-timing-458306-m4')

# 2. Nokta ve Bölge Tanımı
lon, lat = -82.727005, 27.989324          # Örnek: İstanbul koordinatları
point = ee.Geometry.Point([lon, lat])
region = point.buffer(100).bounds()    # 500m yarıçaplı kare bölge

# 3. Sentinel-2 Koleksiyonundan Filtreleme
collection = (
    ee.ImageCollection('USDA/NAIP/DOQQ')
    .filterBounds(point)
    .filterDate('2017-01-01', '2025-04-29')
    .sort('SYSTEM:TIME_START', False)   # En yeni görüntü başta
)
image = collection.first()

# 4. Görselleştirme Parametreleri (RGB)
vis_params = {
    'bands': ['R', 'G', 'B'],
    'min': 0,
    'max': 255
}

region_geojson = region.getInfo()
coords = region_geojson['coordinates'][0]


# 5. Thumbnail URL Oluşturma ve Yazdırma
thumb_url = image.getThumbURL({
    'bands': vis_params['bands'],
    'min': vis_params['min'],
    'max': vis_params['max'],
    'dimensions': [2000, 2000],
    'region': region.getInfo()        # GeoJSON formatında bölge
})
print(f"Thumbnail URL: {thumb_url}")

# # 6. Google Drive’a GeoTIFF Olarak Export
# task = ee.batch.Export.image.toDrive(
#     image=image.visualize(**vis_params),
#     description='Location_RGB_Export',
#     folder='GEE_Exports',
#     fileNamePrefix='location_500m',
#     region=coords,
#     scale=10,
#     fileFormat='GeoTIFF'
# )
# task.start()
# print("Export görevi başlatıldı. Earth Engine görevler panelinden durumunu kontrol edebilirsin.")
